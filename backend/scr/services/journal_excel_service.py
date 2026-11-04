"""
Разбор Excel-выгрузки ЕРИСО КО (Приложение Б) без обращения к БД.
"""
import datetime
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass, field

from openpyxl import load_workbook

from scr.services.text_service import TextNormalizationService

MAX_ERRORS = 20
_COLUMNS = 9

_LATIN_TO_CYRILLIC = str.maketrans("ABCEHKMOPTX", "АВСЕНКМОРТХ")


@dataclass(frozen=True)
class JournalRow:
    row_number: int
    class_name: str
    student_name: str
    subject_name: str
    lesson_date: datetime.date
    topic: str | None
    homework: str | None
    grade: int | None
    work_type: str = "regular"
    homework_status: str | None = None


@dataclass
class LessonSpec:
    class_id: int
    subject_id: int
    lesson_date: datetime.date
    topic: str | None
    homework: str | None
    sequence: int = 0


@dataclass
class ResolveResult:
    lessons: dict = field(default_factory=dict)
    grades: dict = field(default_factory=dict)  # (lesson_key, student_id) -> (value, work_type, homework_status)
    errors: list = field(default_factory=list)
    skipped_rows: int = 0


def normalize_text(value: str) -> str:
    return TextNormalizationService.topic_normalized(value)


def normalize_class_name(value: str) -> str:
    compact = re.sub(r"\s+", "", str(value)).upper()
    return compact.translate(_LATIN_TO_CYRILLIC)


def student_key(full_name: str) -> str:
    return " ".join(normalize_text(full_name).split()[:2])


def build_student_index(rows) -> dict:
    index: dict = defaultdict(lambda: defaultdict(list))
    for user_id, full_name, class_id in rows:
        index[class_id][student_key(full_name)].append(user_id)
    return index


def work_type_from_label(label: str | None) -> str:
    text = normalize_text(label or "")
    if not text:
        return "regular"
    if "впр" in text:
        return "vpr"
    if "контрол" in text or "провероч" in text or "экзамен" in text:
        return "control"
    if text in ("дз", "д з") or "домаш" in text:
        return "homework"
    return "regular"


def academic_year_for(date: datetime.date) -> int:
    return date.year if date.month >= 9 else date.year - 1


def quarter_for(date: datetime.date) -> int:
    if date.month in (9, 10): return 1
    if date.month in (11, 12): return 2
    if date.month in (1, 2, 3): return 3
    return 4


def synthetic_lesson_id(school_id: int, class_id: int, subject_id: int, lesson_date: datetime.date, sequence: int) -> uuid.UUID:
    school_ns = uuid.uuid5(uuid.NAMESPACE_DNS, f"smart-diary-school-{school_id}")
    return uuid.uuid5(school_ns, f"{class_id}|{subject_id}|{lesson_date.isoformat()}|{sequence}")


def _to_date(value) -> datetime.date | None:
    if isinstance(value, datetime.datetime): return value.date()
    if isinstance(value, datetime.date): return value
    if isinstance(value, str):
        text = value.strip()
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y"):
            try: return datetime.datetime.strptime(text, fmt).date()
            except ValueError: continue
    return None


def _to_grade(value) -> int | None:
    if value is None: return None
    if isinstance(value, bool): return None
    if isinstance(value, (int, float)):
        number = value
    else:
        text = str(value).strip().replace(",", ".")
        if not re.fullmatch(r"\d+(\.0+)?", text): return None
        number = float(text)
    if number != int(number) or not 1 <= int(number) <= 5:
        raise ValueError("оценка должна быть целым числом от 1 до 5")
    return int(number)


def _clean(value) -> str | None:
    if value is None: return None
    text = str(value).strip()
    return text or None


def parse_journal_excel(file_path: str) -> tuple[list[JournalRow], list[str]]:
    rows: list[JournalRow] = []
    errors: list[str] = []
    workbook = load_workbook(filename=file_path, read_only=True, data_only=True)
    try:
        sheet = workbook.active
        for index, raw in enumerate(sheet.iter_rows(values_only=True)):
            if index == 0: continue
            cells = list(raw) + [None] * (_COLUMNS - len(raw))
            if all(c is None or str(c).strip() == "" for c in cells): continue
            number = index + 1

            class_name, student, subject = (_clean(cells[0]), _clean(cells[1]), _clean(cells[2]))
            if not (class_name and student and subject):
                errors.append(f"Строка {number}: не заполнены класс, ФИО или предмет")
                continue
            lesson_date = _to_date(cells[3])
            if lesson_date is None:
                errors.append(f"Строка {number}: некорректная дата «{cells[3]}»")
                continue
            try:
                grade = _to_grade(cells[8])
            except ValueError as exc:
                errors.append(f"Строка {number}: {exc} (в файле «{cells[8]}»)")
                continue

            # Читаем статус ДЗ (колонка G)
            homework_status = _clean(cells[6])
            if homework_status:
                homework_status = homework_status.lower()

            rows.append(
                JournalRow(
                    row_number=number,
                    class_name=class_name,
                    student_name=student,
                    subject_name=subject,
                    lesson_date=lesson_date,
                    topic=_clean(cells[4]),
                    homework=_clean(cells[5]),
                    grade=grade,
                    work_type=work_type_from_label(_clean(cells[7])),
                    homework_status=homework_status,
                )
            )
    finally:
        workbook.close()
    return rows, errors


def resolve_rows(rows, assignments: dict, students_by_class: dict) -> ResolveResult:
    result = ResolveResult()
    seen_errors: set = set()

    def add_error(key, message: str) -> None:
        if key not in seen_errors:
            seen_errors.add(key)
            result.errors.append(message)

    for row in rows:
        pair = (normalize_class_name(row.class_name), normalize_text(row.subject_name))
        assignment = assignments.get(pair)
        if assignment is None:
            result.skipped_rows += 1
            add_error(("assignment", pair), f"Строка {row.row_number}: у вас нет предмета «{row.subject_name}» в классе «{row.class_name}»")
            continue
        class_id, subject_id = assignment

        topic_norm = normalize_text(row.topic) if row.topic else ""
        lesson_key = (class_id, subject_id, row.lesson_date, topic_norm)
        spec = result.lessons.get(lesson_key)
        if spec is None:
            spec = LessonSpec(class_id=class_id, subject_id=subject_id, lesson_date=row.lesson_date, topic=row.topic, homework=row.homework)
            result.lessons[lesson_key] = spec
        elif spec.homework is None and row.homework:
            spec.homework = row.homework

        ids = students_by_class.get(class_id, {}).get(student_key(row.student_name), [])
        if len(ids) == 1:
            # Сохраняем даже если оценка None (важно для статуса ДЗ)
            result.grades[(lesson_key, ids[0])] = (row.grade, row.work_type, row.homework_status)
        elif not ids:
            add_error(("student", class_id, student_key(row.student_name)), f"Строка {row.row_number}: ученик «{row.student_name}» не найден в классе «{row.class_name}», оценка пропущена")
        else:
            add_error(("student", class_id, student_key(row.student_name)), f"Строка {row.row_number}: в классе «{row.class_name}» несколько учеников «{row.student_name}», оценка пропущена")

    per_day: dict = defaultdict(int)
    for (class_id, subject_id, date, _topic), spec in result.lessons.items():
        day = (class_id, subject_id, date)
        spec.sequence = per_day[day]
        per_day[day] += 1
    return result