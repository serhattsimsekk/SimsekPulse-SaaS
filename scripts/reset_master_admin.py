#!/usr/bin/env python
"""Master admin hesabını sıfırlayan bağımsız (standalone) script.

Bu script, projenin geri kalanından bağımsız olarak da çalıştırılabilecek
şekilde tasarlanmıştır: proje kökünü kendisi `sys.path`'e ekler, `.env`
dosyasını kendisi yükler ve doğrudan bir veritabanı bağlantısı açar.

NEDEN passlib/bcrypt DEĞİL, projenin kendi hash algoritması kullanılıyor?
--------------------------------------------------------------------
Projede şifreler `services/security.py` içindeki `hash_password()` ile
`pbkdf2_sha256$<rounds>$<salt>$<hash>` formatında saklanıyor ve girişte
`verify_password()` SADECE bu formatı tanıyor (bkz. `api/routes/auth.py`
`/login` endpoint'i). Eğer bu script şifreyi passlib/bcrypt ile
hash'leseydi, kaydedilen hash `pbkdf2_sha256$` ile başlamayacağından
`verify_password()` onu anında geçersiz sayar ve giriş YİNE başarısız
olurdu. Bu yüzden script kasıtlı olarak projenin gerçek
`hash_password()`/`verify_password()` fonksiyonlarını kullanır; böylece
üretilen hash, login endpoint'inin beklediği formatla birebir uyumludur.

Kullanım
--------
Sunucuda, API container'ı içinden (proje kök dizininin volume/COPY ile
mevcut olduğu ortamda) çalıştırın:

    docker compose exec -T api python scripts/reset_master_admin.py

Belirli bir şifre vermek isterseniz:

    docker compose exec -T api python scripts/reset_master_admin.py --password "YeniGuvenliSifre123!"

Farklı bir tenant kodu / e-posta ile çalıştırmak isterseniz:

    docker compose exec -T api python scripts/reset_master_admin.py --tenant-code master --email admin@simseklog.com

Script şunları garanti eder:
  1. `.env` dosyasındaki `ADMIN_SEED_PASSWORD` (veya `--password` ile
     verilen değer) okunur.
  2. `master` tenant'ı yoksa oluşturulur; varsa `is_active=true` ve
     `subscription_status='active'` olacak şekilde güncellenir (lisans
     geçerli hale getirilir).
  3. `admin@simseklog.com` kullanıcısı yoksa oluşturulur, varsa şifresi
     projenin kendi güvenli hash algoritmasıyla yeniden hash'lenir,
     `is_active=true` yapılır ve hesap kilidi (`locked_until`,
     `failed_login_attempts`) sıfırlanır.
  4. İşlem sonunda net bir başarı özeti konsola basılır.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# --- sys.path ayarı ------------------------------------------------------
# Bu script `scripts/` alt klasöründe yaşıyor; proje kökü (services/,
# database/ paketlerinin bulunduğu dizin) bir üst dizindir. Script nereden
# çalıştırılırsa çalıştırılsın (ör. `python scripts/reset_master_admin.py`
# veya `cd scripts && python reset_master_admin.py`) `import services...`
# ve `import database...` ifadelerinin çalışabilmesi için proje kökünü
# açıkça `sys.path`'in başına ekliyoruz.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

# `.env` dosyasını, diğer modüller (database.session vb.) os.getenv() ile
# ortam değişkenlerini okumadan ÖNCE yüklüyoruz; böylece DATABASE_URL,
# ADMIN_SEED_PASSWORD gibi değerler script bağımsız çalıştırıldığında da
# doğru okunur.
load_dotenv(PROJECT_ROOT / ".env")

from sqlalchemy import text  # noqa: E402

from database.session import SessionLocal  # noqa: E402
from services.security import hash_password  # noqa: E402


def reset_master_admin(tenant_code: str, email: str, password: str) -> dict:
    """Master tenant'ı ve admin kullanıcısını verilen şifreyle sıfırlar.

    Idempotent'tir: birden fazla kez çalıştırmak güvenlidir.
    """
    tenant_code = tenant_code.strip().lower()
    email = email.strip().lower()

    with SessionLocal() as db:
        tenant_id = db.execute(
            text("SELECT id::text FROM tenants WHERE LOWER(code) = :code"),
            {"code": tenant_code},
        ).scalar_one_or_none()

        tenant_created = tenant_id is None
        if tenant_created:
            tenant_id = db.execute(
                text(
                    "INSERT INTO tenants (name, code, is_active, subscription_status) "
                    "VALUES (:name, :code, true, 'active') RETURNING id::text"
                ),
                {"name": "ŞimşekLog SaaS Master", "code": tenant_code},
            ).scalar_one()
        else:
            db.execute(
                text(
                    "UPDATE tenants SET is_active = true, subscription_status = 'active' "
                    "WHERE id::text = :tenant_id"
                ),
                {"tenant_id": tenant_id},
            )

        # `users` tablosundaki Row-Level Security (RLS) politikası,
        # doğrulanmış tenant_id işlem-yerel (transaction-local) olarak set
        # edilmeden sorgulandığında/yazılamadığında satırı görünmez kılar ya
        # da INSERT/UPDATE'i reddeder (bkz. auth.py/seed.py'deki aynı
        # gerekçe). Bu yüzden ilgili tenant için açıkça set ediyoruz.
        db.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
            {"tenant_id": tenant_id},
        )

        user_row = db.execute(
            text(
                "SELECT id::text FROM users "
                "WHERE tenant_id::text = :tenant_id AND LOWER(username) = :email"
            ),
            {"tenant_id": tenant_id, "email": email},
        ).scalar_one_or_none()

        password_hash = hash_password(password)
        user_created = user_row is None
        if user_created:
            user_id = db.execute(
                text(
                    "INSERT INTO users (tenant_id, name, username, role, department, "
                    "password_hash, is_active, failed_login_attempts, locked_until) "
                    "VALUES (CAST(:tenant_id AS uuid), :name, :username, 'super_admin', "
                    "'executive', :password_hash, true, 0, NULL) RETURNING id::text"
                ),
                {
                    "tenant_id": tenant_id,
                    "name": "SaaS Master Admin",
                    "username": email,
                    "password_hash": password_hash,
                },
            ).scalar_one()
        else:
            user_id = user_row
            db.execute(
                text(
                    "UPDATE users SET role = 'super_admin', department = 'executive', "
                    "is_active = true, password_hash = :password_hash, "
                    "failed_login_attempts = 0, locked_until = NULL "
                    "WHERE id::text = :user_id"
                ),
                {"password_hash": password_hash, "user_id": user_id},
            )

        db.commit()

        return {
            "tenant_id": tenant_id,
            "tenant_code": tenant_code,
            "tenant_created": tenant_created,
            "user_id": user_id,
            "email": email,
            "user_created": user_created,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--tenant-code",
        default=os.getenv("MASTER_TENANT_CODE", "master"),
        help="Sıfırlanacak şirket kodu (varsayılan: master / MASTER_TENANT_CODE ortam değişkeni).",
    )
    parser.add_argument(
        "--email",
        default=os.getenv("MASTER_ADMIN_EMAIL", "admin@simseklog.com"),
        help="Sıfırlanacak admin e-postası (varsayılan: admin@simseklog.com / MASTER_ADMIN_EMAIL).",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Yeni şifre. Verilmezse ADMIN_SEED_PASSWORD, o da yoksa MASTER_ADMIN_PASSWORD "
        "ortam değişkeni (.env dosyasından) kullanılır.",
    )
    args = parser.parse_args()

    password = args.password or os.getenv("ADMIN_SEED_PASSWORD") or os.getenv("MASTER_ADMIN_PASSWORD")
    if not password:
        print(
            "HATA: Şifre bulunamadı. --password ile verin ya da .env içinde "
            "ADMIN_SEED_PASSWORD (veya MASTER_ADMIN_PASSWORD) tanımlayın.",
            file=sys.stderr,
        )
        return 1

    try:
        result = reset_master_admin(args.tenant_code, args.email, password)
    except Exception as exc:  # pragma: no cover - operasyonel script
        print(f"HATA: Master admin sıfırlanamadı: {exc}", file=sys.stderr)
        return 1

    print("=" * 64)
    print("MASTER ADMIN SIFIRLAMA BASARILI")
    print("=" * 64)
    print(f"Tenant kodu       : {result['tenant_code']} ({'oluşturuldu' if result['tenant_created'] else 'zaten vardı, güncellendi'})")
    print(f"Tenant ID         : {result['tenant_id']}")
    print(f"Tenant durumu     : is_active=true, subscription_status='active'")
    print(f"Admin e-posta     : {result['email']} ({'oluşturuldu' if result['user_created'] else 'zaten vardı, güncellendi'})")
    print(f"Kullanıcı ID      : {result['user_id']}")
    print("Kullanıcı durumu  : is_active=true, hesap kilidi açıldı, şifre yeniden hash'lendi")
    print("-" * 64)
    print("Artık şu bilgilerle giriş yapabilirsiniz:")
    print(f"  Şirket kodu : {result['tenant_code']}")
    print(f"  E-posta     : {result['email']}")
    print("  Şifre       : .env dosyasındaki ADMIN_SEED_PASSWORD değeri (veya --password ile verdiğiniz değer)")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
