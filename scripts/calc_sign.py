"""Считает признак риска по годовой отчётности из data/girbo_raw.json.

Признак есть, если выполнены оба условия:
  1) стр. 4100 < 0, денег от текущих операций не хватает на уплату процентов (стр. 4123 входит в 4100);
  2) стр. 2330 > 0 и стр. 2300 + стр. 2330 < 1,5 * стр. 2330.

    python scripts/calc_sign.py
"""
import io
import json
import sys
from datetime import date
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAW = Path(__file__).resolve().parent.parent / "data" / "girbo_raw.json"

# первая найденная просрочка платежа по облигациям, даже если её потом закрыли
FIRST_NONPAYMENT = {
    "Концессии водоснабжения Саратов": "2024-12-09",
    "Селлер (Техпорт)": "2024-10-11",
    "Русская Контейнерная Компания": "2023-12-21",
    "Гарант-Инвест Коммерческая недвижимость": "2025-03-14",
    "Кузина": "2024-06-18",
    "Феррони": "2025-01-10",
    "Нафтатранс плюс": "2025-06-16",
    "ТК Магнум Ойл": "2025-06-17",
    "УК Доминион": "2025-08-20",
    "С-Принт": "2025-07-23",
    "Мосрегионлифт": "2025-06-16",
    "ГазТрансСнаб": "2025-07-29",
    "Монополия": "2025-12-04",
}

# не входят в расчёт
EXCLUDED = {
    "РЕАТОРГ": "нет в ГИР БО",
    "ПРОМ ГАРАНТ": "упрощённая отчётность без отчёта о движении денежных средств",
    "Чистая Планета": "в отчёте за 2024 год нет движения денежных средств",
    "Строй Система Механизация": "дата дефолта не подтверждена, отчёт за 2024 год опубликован после дефолта",
    "СтанкоМашСтрой": "нет в ГИР БО",
}


def lines(bfo):
    c = bfo["typeCorrections"][0]["correction"]
    fm, fr = c.get("fundsMovement") or {}, c.get("financialResult") or {}
    return fm.get("current4100"), fm.get("current4123"), fr.get("current2300"), fr.get("current2330")


def sign(s4100, s2330, s2300):
    cond1 = s4100 < 0
    cond2 = s2330 > 0 and s2300 + s2330 < 1.5 * s2330
    return cond1, cond2, cond1 and cond2


def months(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days / 30.4375


def main():
    data = json.loads(RAW.read_text(encoding="utf-8"))
    counted = total_def = 0
    print("С дефолтом")
    for c in data:
        if c["group"] != "default":
            continue
        if c["name"] in EXCLUDED:
            print(f"  {c['name']}: не в расчёте, {EXCLUDED[c['name']]}")
            continue
        total_def += 1
        bfo = max((b for b in c["bfo"] if b["actualBfoDate"] < c["event"]), key=lambda b: b["actualBfoDate"])
        s4100, s4123, s2300, s2330 = lines(bfo)
        c1, c2, s = sign(s4100, s2330, s2300)
        first = FIRST_NONPAYMENT[c["name"]]
        before = bfo["actualBfoDate"] < first
        ok = s and before
        counted += ok
        lead = f", за {months(bfo['actualBfoDate'], first):.1f} мес." if ok else ""
        print(f"  {c['name'][:38]:38} отчёт {bfo['period']} от {bfo['actualBfoDate']}  4100={s4100:>13,.0f}  "
              f"2300={s2300:>12,.0f}  2330={s2330:>12,.0f}  усл.1={'да' if c1 else 'нет'}  усл.2={'да' if c2 else 'нет'}  "
              f"до первой неуплаты {first}={'да' if before else 'нет'}  в счёт={'да' if ok else 'нет'}{lead}")
    print(f"Итого признак до неуплаты: {counted} из {total_def}\n")

    flagged = total_con = 0
    print("Без дефолта, отчёт за 2024 год")
    for c in data:
        if c["group"] != "control":
            continue
        if c["name"] in EXCLUDED or not c.get("bfo"):
            print(f"  {c['name']}: не в расчёте, {EXCLUDED.get(c['name'], 'нет данных')}")
            continue
        total_con += 1
        bfo = next(b for b in c["bfo"] if b["period"] == "2024")
        s4100, s4123, s2300, s2330 = lines(bfo)
        c1, c2, s = sign(s4100, s2330, s2300)
        flagged += s
        print(f"  {c['name'][:38]:38} 4100={s4100:>13,.0f}  2300={s2300:>12,.0f}  2330={s2330:>12,.0f}  "
              f"усл.1={'да' if c1 else 'нет'}  усл.2={'да' if c2 else 'нет'}  признак={'да' if s else 'нет'}")
    print(f"Итого признак: {flagged} из {total_con}")


if __name__ == "__main__":
    main()
