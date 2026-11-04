import io
import math
import os
import uuid
from PIL import Image, ImageDraw, ImageFont
import magic

from scr.config import settings


class ImageProcessingService:

    @staticmethod
    def _load_font(size: int) -> ImageFont.FreeTypeFont:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "C:\\Windows\\Fonts\\arialbd.ttf",
            "C:\\Windows\\Fonts\\Arial.ttf",
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except OSError:
                    continue
        return ImageFont.load_default()

    @staticmethod
    def _draw_fitted_text(draw, text, box, font_fn, fill, min_size=11, max_size=22):
        x1, y1, x2, y2 = box
        w, h = x2 - x1, y2 - y1
        for size in range(max_size, min_size - 1, -1):
            font = font_fn(size)
            bbox = draw.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            if tw <= w - 12 and th <= h - 8:
                cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                draw.text(
                    (cx - tw / 2 - bbox[0], cy - th / 2 - bbox[1]),
                    text,
                    font=font,
                    fill=fill,
                )
                return
        font = font_fn(min_size)
        draw.text(
            ((x1 + x2) / 2, (y1 + y2) / 2), text, font=font, fill=fill, anchor="mm"
        )

    @classmethod
    def generate_seating_png(
        cls,
        layout_json: dict,
        teacher_position: str = "front_center",
        class_name: str | None = None,
    ) -> io.BytesIO:
        """
        Новая улучшенная отрисовка рассадки (интеграция make_one).
        Принимает layout_json с матрицей grid и массивом seats из СУБД.
        """
        W, H = 1600, 1200
        S = 2  # Суперсэмплинг для сглаживания
        img = Image.new("RGB", (W * S, H * S), "#F4F7FA")
        draw = ImageDraw.Draw(img)

        COLOR_DESK = "#FFFFFF"
        COLOR_SEAT_TAKEN = "#4A5D73"
        COLOR_SEAT_EMPTY = "#D0DFEB"
        COLOR_TITLE = "#4A5D73"
        COLOR_SUBTITLE = "#7B8A99"
        COLOR_TEACHER = "#4A5D73"
        COLOR_WHITE = "#FFFFFF"

        _cache: dict[int, ImageFont.FreeTypeFont] = {}

        def font_of(size: int):
            k = size * S
            if k not in _cache:
                _cache[k] = cls._load_font(k)
            return _cache[k]

        grid_cfg = layout_json.get("grid", {"rows": 5, "cols": 6})
        rows = max(1, int(grid_cfg.get("rows", 5)))
        cols = max(1, int(grid_cfg.get("cols", 6)))

        # Конвертируем матричное хранение СУБД (row, col) в упорядоченную структуру.
        # ТЗ подразумевает, что cols — это количество мест (обычно 3 ряда парт по 2 места = 6 колонок).
        # Каждая парта объединяет пару мест: (r, c) и (r, c+1) при четных c.
        db_seats = layout_json.get("seats", [])
        seats_matrix = {}
        for s in db_seats:
            seats_matrix[(s.get("row"), s.get("col"))] = s

        # ---- заголовок ----
        margin = 40 * S
        title_h = 70 * S
        title_text = f"Рассадка — {class_name}" if class_name else "Рассадка класса"

        draw.text(
            (W * S // 2, margin + title_h // 2),
            title_text,
            fill=COLOR_TITLE,
            font=font_of(34),
            anchor="mm",
        )

        # ---- стол учителя ----
        teacher_w, teacher_h = 360 * S, 60 * S
        if teacher_position == "front_left":
            tx1 = margin
        elif teacher_position == "front_right":
            tx1 = W * S - margin - teacher_w
        else:
            tx1 = (W * S - teacher_w) // 2
        ty1 = margin + title_h + 10 * S
        ty2 = ty1 + teacher_h
        draw.rounded_rectangle(
            [tx1, ty1, tx1 + teacher_w, ty2],
            radius=int(teacher_h // 2),
            fill=COLOR_TEACHER,
        )
        draw.text(
            ((tx1 + tx1 + teacher_w) / 2, (ty1 + ty2) / 2),
            "СТОЛ УЧИТЕЛЯ",
            fill=COLOR_WHITE,
            font=font_of(20),
            anchor="mm",
        )

        grid_top = ty2 + 30 * S
        grid_bottom = H * S - margin
        grid_left = margin
        grid_right = W * S - margin
        grid_w = grid_right - grid_left
        grid_h = grid_bottom - grid_top

        # Вычисляем размеры парт. В make_one одна итерация цикла рисует ОДНУ ПАРТУ (на ней 2 сиденья).
        # Следовательно, количество физических рядов парт = rows, а количество парт в ряду = cols // 2.
        desk_cols = max(1, cols // 2)
        desk_w = grid_w / desk_cols
        desk_h = grid_h / rows
        desk_gap = 12 * S

        for r in range(rows):
            for dc in range(desk_cols):
                x1 = grid_left + dc * desk_w + desk_gap
                y1 = grid_top + r * desk_h + desk_gap
                x2 = x1 + desk_w - 2 * desk_gap
                y2 = y1 + desk_h - 2 * desk_gap

                # Рисуем парту
                draw.rounded_rectangle([x1, y1, x2, y2], radius=28 * S, fill=COLOR_DESK)

                pad_x = (x2 - x1) * 0.06
                pad_y = (y2 - y1) * 0.18
                seat_w = (x2 - x1 - 3 * pad_x) / 2
                seat_h = (y2 - y1) - 2 * pad_y
                seat_r = int(min(seat_h // 2, seat_w // 2))

                # Рисуем 2 стула у этой парты
                for i in range(2):
                    sx1 = x1 + pad_x + i * (seat_w + pad_x)
                    sy1 = y1 + pad_y
                    sx2 = sx1 + seat_w
                    sy2 = sy1 + seat_h

                    # Вычисляем реальную колонку в матрице СУБД
                    actual_col = dc * 2 + i
                    seat_data = seats_matrix.get((r, actual_col))

                    if seat_data:
                        draw.rounded_rectangle(
                            [sx1, sy1, sx2, sy2], radius=seat_r, fill=COLOR_SEAT_TAKEN
                        )

                        # Отображаем имя или ФИО (если подгружено), иначе ID
                        name = (
                            seat_data.get("student_name")
                            or seat_data.get("full_name")
                            or f"№{seat_data.get('student_id', '?')}"
                        )

                        cls._draw_fitted_text(
                            draw,
                            name,
                            [sx1, sy1, sx2, sy2],
                            font_of,
                            COLOR_WHITE,
                            min_size=11,
                            max_size=22,
                        )
                    else:
                        draw.rounded_rectangle(
                            [sx1, sy1, sx2, sy2], radius=seat_r, fill=COLOR_SEAT_EMPTY
                        )

        # Возвращаем к оригинальному размеру с качественным сглаживанием LANCZOS
        img = img.resize((W, H), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        img.save(out, format="PNG", optimize=True)
        out.seek(0)
        return out

    @staticmethod
    def validate_and_save_photo(file_bytes: bytes, filename: str, class_id: int) -> str:
        mime = magic.from_buffer(file_bytes, mime=True)
        if mime not in ["image/png", "image/jpeg"]:
            raise ValueError("Недопустимый формат файла. Разрешены только PNG и JPEG.")

        input_image = Image.open(io.BytesIO(file_bytes))
        resized_image = input_image.resize((1600, 1200), Image.Resampling.LANCZOS)

        photos_dir = getattr(settings, "PHOTOS_DIR", "/tmp/photos")
        os.makedirs(photos_dir, exist_ok=True)

        new_filename = f"{class_id}_{uuid.uuid4().hex}.png"
        file_path = os.path.join(photos_dir, new_filename)

        resized_image.save(file_path, format="PNG")
        return new_filename
