"""Master tenant/admin durumunu sunucuda güvenli şekilde denetlemek ve
gerekirse sıfırlamak için yardımcı script.

Kullanım (sunucuda, API container'ı içinden çalıştırın):

    # Sadece durumu göster (hiçbir şey değiştirmez):
    docker compose exec -T api python scripts/check_master_admin.py

    # Master tenant'ı ve admin kullanıcısını .env/.env.production içindeki
    # ADMIN_SEED_PASSWORD (veya MASTER_ADMIN_PASSWORD) ile sıfırla:
    docker compose exec -T api python scripts/check_master_admin.py --reset

    # Belirli bir şifre ile sıfırlamak isterseniz:
    docker compose exec -T api python scripts/check_master_admin.py --reset --password "YeniGuvenliSifre123!"

Bu script şunları kontrol/onarır:
  - tenants.is_active, tenants.subscription_status ("active" olmalı)
  - users.is_active (true olmalı)
  - users.failed_login_attempts / users.locked_until (hesap kilidini açar)
  - users.password_hash (--reset verilirse, services.security.hash_password
    ile ayni algoritma kullanilarak yeniden hash'lenir; boylece auth.py'deki
    verify_password ile birebir uyumlu olur)

Hiçbir şeyi --reset bayrağı verilmeden DEĞİŞTİRMEZ; varsayılan çalıştırma
salt-okunur bir tanı raporudur.
"""
from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import text

from database.session import SessionLocal
from services.security import hash_password


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tenant-code",
        default=os.getenv("MASTER_TENANT_CODE", "master"),
        help="Kontrol edilecek şirket kodu (varsayılan: master / MASTER_TENANT_CODE).",
    )
    parser.add_argument(
        "--email",
        default=os.getenv("MASTER_ADMIN_EMAIL", "admin@simseklog.com"),
        help="Kontrol edilecek admin e-postası (varsayılan: admin@simseklog.com / MASTER_ADMIN_EMAIL).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Tenant'ı aktifleştir, kullanıcıyı aktifleştir/kilidini aç ve şifreyi yeniden hash'le.",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="--reset ile birlikte kullanılacak yeni şifre. Verilmezse ADMIN_SEED_PASSWORD "
        "veya MASTER_ADMIN_PASSWORD ortam değişkeni kullanılır.",
    )
    args = parser.parse_args()

    tenant_code = args.tenant_code.strip().lower()
    email = args.email.strip().lower()

    with SessionLocal() as db:
        tenant = db.execute(
            text(
                "SELECT id::text, name, code, is_active, subscription_status "
                "FROM tenants WHERE LOWER(code) = :code"
            ),
            {"code": tenant_code},
        ).mappings().first()

        if tenant is None:
            print(f"HATA: '{tenant_code}' kodlu tenant bulunamadı.")
            return 1

        print("--- Tenant ---")
        print(f"id                 : {tenant['id']}")
        print(f"name               : {tenant['name']}")
        print(f"code               : {tenant['code']}")
        print(f"is_active          : {tenant['is_active']}")
        print(f"subscription_status: {tenant['subscription_status']}")

        # Bu tenant'a ait `users` satırlarını görebilmek için RLS oturum
        # değişkenini set etmemiz gerekir (bkz. auth.py/seed.py'deki aynı
        # gerekçe: app.tenant_id set edilmezse RLS satırı gizler).
        db.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
            {"tenant_id": tenant["id"]},
        )

        user = db.execute(
            text(
                "SELECT id::text, username, role, is_active, failed_login_attempts, "
                "locked_until, password_hash FROM users "
                "WHERE tenant_id::text = :tenant_id AND LOWER(username) = :email"
            ),
            {"tenant_id": tenant["id"], "email": email},
        ).mappings().first()

        print("\n--- Kullanıcı ---")
        if user is None:
            print(f"HATA: '{email}' kullanıcısı bu tenant altında bulunamadı.")
            if not args.reset:
                return 1
        else:
            print(f"id                    : {user['id']}")
            print(f"username              : {user['username']}")
            print(f"role                  : {user['role']}")
            print(f"is_active             : {user['is_active']}")
            print(f"failed_login_attempts : {user['failed_login_attempts']}")
            print(f"locked_until          : {user['locked_until']}")
            print(f"password_hash (prefix): {(user['password_hash'] or '')[:20]}...")

        if not args.reset:
            print("\n(Değişiklik yapılmadı; sıfırlamak için --reset ekleyin.)")
            return 0

        password = args.password or os.getenv("ADMIN_SEED_PASSWORD") or os.getenv("MASTER_ADMIN_PASSWORD")
        if not password:
            print(
                "HATA: --reset için şifre bulunamadı. --password verin ya da "
                "ADMIN_SEED_PASSWORD/MASTER_ADMIN_PASSWORD ortam değişkenini ayarlayın."
            )
            return 1

        db.execute(
            text(
                "UPDATE tenants SET is_active = true, subscription_status = 'active' "
                "WHERE id::text = :tenant_id"
            ),
            {"tenant_id": tenant["id"]},
        )

        new_hash = hash_password(password)
        if user is None:
            db.execute(
                text(
                    "INSERT INTO users (tenant_id, name, username, role, department, "
                    "password_hash, is_active) VALUES (CAST(:tenant_id AS uuid), :name, "
                    ":username, 'super_admin', 'executive', :password_hash, true)"
                ),
                {
                    "tenant_id": tenant["id"],
                    "name": "SaaS Master Admin",
                    "username": email,
                    "password_hash": new_hash,
                },
            )
        else:
            db.execute(
                text(
                    "UPDATE users SET is_active = true, failed_login_attempts = 0, "
                    "locked_until = NULL, password_hash = :password_hash "
                    "WHERE id::text = :user_id"
                ),
                {"password_hash": new_hash, "user_id": user["id"]},
            )
        db.commit()

        print(
            f"\nOK: Tenant '{tenant_code}' aktif edildi, kullanıcı '{email}' aktif/kilidi "
            "açık ve şifre yeniden hash'lendi."
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
