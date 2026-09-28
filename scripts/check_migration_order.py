"""database/migrations/*.sql dosyalarının tablo oluşturma sırasını statik olarak
doğrular.

Bu script, canlı bir Postgres bağlantısına ihtiyaç duymadan şu tür hataları
önceden yakalamak için yazılmıştır:
    ERROR: relation "tires" does not exist
gibi hataların sebebi, bir tablonun `REFERENCES <tablo>(id)` ile referans
verdiği tablodan DAHA ÖNCE oluşturulmasıdır (migration dosyaları
`psql -v ON_ERROR_STOP=1` ile çalıştırıldığından ilk hatada tüm migration
durur).

Kullanım:
    python scripts/check_migration_order.py

Migration dosyaları `deploy.sh` ile aynı sırada (dosya adına göre alfabetik)
işlenir; bu script de aynı sırayı kullanır. Bir tutarsızlık bulunursa
non-zero exit code ile çıkar, böylece CI/pre-deploy adımı olarak da
kullanılabilir.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "database" / "migrations"

# "CREATE TABLE IF NOT EXISTS <name> (" -- tablo adını yakalar.
CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(\w+)\s*\(", re.IGNORECASE
)
# "REFERENCES <name>(" -- FK referans tablosunu yakalar.
REFERENCES_RE = re.compile(r"REFERENCES\s+(\w+)\s*\(", re.IGNORECASE)
# "ALTER TABLE <name>" -- ALTER hedef tablosunu yakalar.
ALTER_TABLE_RE = re.compile(r"ALTER\s+TABLE\s+(?:ONLY\s+)?(\w+)", re.IGNORECASE)


def find_statements(sql: str) -> list[str]:
    """SQL içeriğini noktalı virgülle ayrılmış ifadelere böler (basit, yorum/dizeleri
    dikkate almadan; bu dosyalardaki basit DDL için yeterlidir)."""
    return [stmt.strip() for stmt in sql.split(";") if stmt.strip()]


def check_migrations() -> list[str]:
    errors: list[str] = []
    known_tables: set[str] = set()
    duplicate_locations: dict[str, list[str]] = {}

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migration_files:
        return [f"Hiç migration dosyası bulunamadı: {MIGRATIONS_DIR}"]

    for path in migration_files:
        sql = path.read_text(encoding="utf-8")
        for stmt in find_statements(sql):
            create_match = CREATE_TABLE_RE.search(stmt)
            if create_match:
                table_name = create_match.group(1).lower()

                # Bu CREATE TABLE ifadesi içindeki tüm FK referanslarını kontrol et.
                for ref_match in REFERENCES_RE.finditer(stmt):
                    ref_table = ref_match.group(1).lower()
                    if ref_table != table_name and ref_table not in known_tables:
                        errors.append(
                            f"{path.name}: CREATE TABLE '{table_name}' tablosu, "
                            f"henüz oluşturulmamış '{ref_table}' tablosuna REFERENCES "
                            "veriyor (sıralama hatası)."
                        )

                duplicate_locations.setdefault(table_name, []).append(path.name)
                known_tables.add(table_name)
                continue

            alter_match = ALTER_TABLE_RE.search(stmt)
            if alter_match and not stmt.upper().lstrip().startswith("ALTER TABLE ONLY"):
                target = alter_match.group(1).lower()
                # "ENABLE ROW LEVEL SECURITY" / "ADD COLUMN" gibi ifadeler; tablo
                # zaten var olmalı.
                if target not in known_tables:
                    errors.append(
                        f"{path.name}: ALTER TABLE '{target}' çalıştırılıyor ama bu "
                        "tablo bu noktaya kadar hiç oluşturulmamış."
                    )

    for table_name, files in duplicate_locations.items():
        if len(files) > 1:
            errors.append(
                f"UYARI: '{table_name}' tablosu birden fazla dosyada tanımlanmış: "
                f"{', '.join(files)} (CREATE TABLE IF NOT EXISTS nedeniyle hataya "
                "yol açmaz, ancak ikinci tanımdaki kolonlar sessizce yok sayılır)."
            )

    return errors


def main() -> int:
    errors = check_migrations()
    if not errors:
        print("OK: Tüm migration dosyalarında tablo oluşturma sırası tutarlı.")
        return 0

    print("Migration sıralama kontrolünde sorun(lar) bulundu:\n")
    for err in errors:
        print(f"  - {err}")
    # Sadece "UYARI:" ile başlayanlar bilgilendirme amaçlıdır; gerçek sıralama
    # hataları varsa exit code 1 döner.
    has_fatal = any(not e.startswith("UYARI:") for e in errors)
    return 1 if has_fatal else 0


if __name__ == "__main__":
    sys.exit(main())
