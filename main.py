import csv
import copy
import json
import os
import sys

# === Индексы столбцов (нумерация с нуля) ===
IDX_PRIORITY = 1      # Приоритет конкурса
IDX_CONSENT = 2       # Подано согласие
IDX_SCORES = 4        # Баллы 
IDX_STATUS = 6        # Статус
IDX_ID = 7            # ID участника


def load_config(path="config.json"):
    """Загружает конфиг-файл с настройками."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка чтения {path}: {e}")
        sys.exit(1)


def parse_file(filename):
    """Читает и парсит CSV-файл, возвращает список абитуриентов с нужными полями."""
    if not os.path.exists(filename):
        print(f"Файл {filename} не найден! Пропускаю.")
        return []
    data = []
    try:
        try:
            f = open(filename, encoding='utf-8')
            reader = csv.reader(f, delimiter=';')
            header = next(reader)
        except UnicodeDecodeError:
            f = open(filename, encoding='windows-1251')
            reader = csv.reader(f, delimiter=';')
            header = next(reader)
        for row in reader:
            # Только "Участвуете в конкурсе" и подано согласие
            if row[IDX_STATUS] != 'Участвуете в конкурсе':
                continue
            if row[IDX_CONSENT] == '—':
                continue
            # Пропускаем, если поле баллов пустое или только пробелы
            if not row[IDX_SCORES].strip():
                continue
            # Парсим баллы
            try:
                scores_raw = list(map(int, row[IDX_SCORES].split()))
                while len(scores_raw) < 3:
                    scores_raw.append(0)
                scores = tuple(scores_raw[:3])
            except Exception:
                # Если баллы не числа (например, "Без"), считаем минимальными
                scores = (0, 0, 0)
            data.append({
                'row': row,
                'priority': int(row[IDX_PRIORITY]),
                'scores': scores,
                'id': row[IDX_ID],
            })
        f.close()
    except Exception as e:
        print(f"Ошибка чтения {filename}: {e}")
    return data


def sort_key(x):
    """Ключ сортировки: по сумме баллов (по убыванию)."""
    return -sum(x['scores'])


def process_lists(lists, places):
    """
    Итеративно формирует списки поступающих с учётом приоритетов и согласий.
    Возвращает финальные списки по направлениям.
    """
    lists = [copy.deepcopy(lst) for lst in lists]
    changed = True
    while changed:
        changed = False
        for i, (lst, n_places) in enumerate(zip(lists, places)):
            first_priority = [x for x in lst if x['priority'] == 1]
            first_priority.sort(key=sort_key)
            winners = set(x['id'] for x in first_priority[:n_places])
            for j, other_lst in enumerate(lists):
                if i == j:
                    continue
                before = len(other_lst)
                other_lst[:] = [x for x in other_lst if x['id'] not in winners]
                if len(other_lst) != before:
                    changed = True
            for j, other_lst in enumerate(lists):
                if i == j:
                    continue
                for x in other_lst:
                    if x['priority'] > 1:
                        x['priority'] -= 1
                        changed = True
    return lists


def find_my_place(lst, my_id, n_places):
    """Возвращает место пользователя (или статус) в списке направления."""
    first_priority = [x for x in lst if x['priority'] == 1]
    first_priority.sort(key=sort_key)
    for idx, x in enumerate(first_priority, 1):
        if x['id'] == my_id:
            if idx <= n_places:
                return idx
            else:
                return f'не проходит (место {idx})'
    return 'нет в списке'


def find_min_score(lst, n_places):
    """Возвращает минимальный балл на поступление (сумма баллов последнего проходящего)."""
    first_priority = [x for x in lst if x['priority'] == 1]
    first_priority.sort(key=sort_key)
    if not first_priority:
        return 'нет проходящих'
    # Оставляем только тех, у кого сумма баллов > 0
    nonzero = [x for x in first_priority if sum(x['scores']) > 0]
    if not nonzero:
        return 'нет проходящих'
    if len(nonzero) < n_places or n_places == 0:
        last = nonzero[-1]
    else:
        last = nonzero[n_places-1]
    return sum(last['scores'])


def main():
    """Точка входа: читает конфиг, обрабатывает списки, выводит результат."""
    config = load_config()
    files = config.get("files")
    budget_places = config.get("budget_places")
    my_id = config.get("my_id")
    if not (files and budget_places and my_id):
        print("Ошибка: не все параметры заданы в config.json!")
        sys.exit(1)
    if len(files) != len(budget_places):
        print("Ошибка: количество файлов и мест должно совпадать!")
        sys.exit(1)
    all_lists = [parse_file(f) for f in files]
    final_lists = process_lists(all_lists, budget_places)
    for i, (lst, n_places, fname) in enumerate(zip(final_lists, budget_places, files), 1):
        place = find_my_place(lst, my_id, n_places)
        min_score = find_min_score(lst, n_places)
        print(f'Направление {i} ({fname}):', place, f'(минимальный балл на поступление: {min_score})')


if __name__ == '__main__':
    main() 