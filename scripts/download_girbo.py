"""Скачивает годовую бухгалтерскую отчётность эмитентов из ГИР БО (bo.nalog.gov.ru).

Результат сохраняется в data/girbo_raw.json. ГИР БО может не отвечать на зарубежные IP.
    python scripts/download_girbo.py
"""
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
OUT = Path(__file__).resolve().parent.parent / "data" / "girbo_raw.json"
UA = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

# группа, название, ИНН, дата дефолта из выборки (для компаний с дефолтом)
COMPANIES = [
    ("default", "Концессии водоснабжения Саратов", "6450090478", "2024-12-09"),
    ("default", "Селлер (Техпорт)", "7725791850", "2024-12-23"),
    ("default", "Русская Контейнерная Компания", "7703426268", "2025-02-18"),
    ("default", "Гарант-Инвест Коммерческая недвижимость", "7726637843", "2025-03-14"),
    ("default", "Кузина", "5404373487", "2025-03-18"),
    ("default", "Феррони", "2312128345", "2025-06-03"),
    ("default", "Нафтатранс плюс", "5404345962", "2025-06-16"),
    ("default", "ТК Магнум Ойл", "7705526892", "2025-06-17"),
    ("default", "РЕАТОРГ", "5036117570", "2025-07-22"),
    ("default", "УК Доминион", "7709804389", "2025-08-20"),
    ("default", "ПРОМ ГАРАНТ", "2315160675", "2025-09-17"),
    ("default", "Строй Система Механизация", "7802776136", "2025-10-06"),
    ("default", "С-Принт", "7447165728", "2025-09-22"),
    ("default", "Мосрегионлифт", "7705722209", "2025-10-02"),
    ("default", "ГазТрансСнаб", "6658460424", "2025-10-28"),
    ("default", "Чистая Планета", "5446020589", "2025-12-01"),
    ("default", "Монополия", "7810766685", "2025-12-04"),
    ("control", "Агротек", "4100006268", ""),
    ("control", "ЕнисейАгроСоюз", "2435006523", ""),
    ("control", "Сибирский комбинат хлебопродуктов", "5520900173", ""),
    ("control", "Сергиевское", "5022560904", ""),
    ("control", "ГК Солтон", "2225123372", ""),
    ("control", "ПИР", "7841422483", ""),
    ("control", "Байсэл", "5401995271", ""),
    ("control", "СЕЛЛ-Сервис", "5406780551", ""),
    ("control", "Ист Лоджистикал Системс", "2723098376", ""),
    ("control", "ЗООПТ", "5260461933", ""),
    ("control", "Сергиево-Посадский мясокомбинат", "5042015329", ""),
    ("control", "Простая еда", "1215229593", ""),
    ("control", "ПЛАЗА-Телеком", "5047104371", ""),
    ("control", "Истринская сыроварня", "5024171100", ""),
    ("control", "Бианка Премиум", "7719857936", ""),
    ("control", "Сибирское стекло", "5406305355", ""),
    ("control", "Электроаппарат", "6312147088", ""),
    ("control", "Новосибирский завод резки металла", "5405963591", ""),
    ("control", "Реиннольц", "5406697416", ""),
    ("control", "УПТК-65", "7801485085", ""),
    ("control", "РДВ Технолоджи", "9721088350", ""),
    ("control", "Феррум", "5263039350", ""),
    ("control", "СтанкоМашСтрой", "5835103100", ""),
    ("control", "Кеарли Групп", "9715397054", ""),
    ("control", "ХРОМОС Инжиниринг", "5249111131", ""),
    ("control", "Нео-Пак", "5404475633", ""),
    ("control", "Стеллар Груп Рус", "7714419590", ""),
    ("control", "ПЭТ ПЛАСТ", "5403040189", ""),
    ("control", "Транс-Миссия", "7805688897", ""),
    ("control", "Сегежа Групп", "9703024202", ""),
]


def get(url):
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # сеть ГИР БО иногда рвётся, пробуем ещё раз
            last = e
            time.sleep(2 + attempt * 2)
    raise last


def main():
    OUT.parent.mkdir(exist_ok=True)
    result = []
    for group, name, inn, event in COMPANIES:
        row = {"group": group, "name": name, "inn": inn, "event": event}
        try:
            s = get("https://bo.nalog.gov.ru/advanced-search/organizations/search?query=" + urllib.parse.quote(inn) + "&page=0")
            content = [c for c in (s.get("content") or []) if str(c.get("inn")) == inn] or (s.get("content") or [])
            if not content:
                row["error"] = "не найдена"
            else:
                org = content[0]
                row["org"] = {"id": org.get("id"), "name": org.get("shortName") or org.get("fullName")}
                row["bfo"] = get(f"https://bo.nalog.gov.ru/nbo/organizations/{org.get('id')}/bfo/")
        except Exception as e:
            row["error"] = f"{type(e).__name__}: {e}"
        result.append(row)
        status = row.get("error") or f"отчётов {len(row.get('bfo') or [])}"
        print(f"{group:8} {name[:40]:40} {status}")
        OUT.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        time.sleep(0.7)
    print("Готово, сохранено в", OUT)


if __name__ == "__main__":
    main()
