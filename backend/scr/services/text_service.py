import re
import unicodedata


class TextNormalizationService:

    @staticmethod
    def topic_normalized(text_input: str) -> str:
        """
        Канонизирует форму темы урока для точного матчинга долгов (§10.2.1 ТЗ).
        Выполняет: strip, lower, ё->е, NFKC, удаление пунктуации и схлопывание пробелов.
        """
        if not text_input:
            return ""

        # 1. Стрип и нижний регистр
        t = text_input.strip().lower()

        # 2. Замена ё на е
        t = t.replace("ё", "е")

        # 3. Unicode-нормализация NFKC
        t = unicodedata.normalize("NFKC", t)

        # 4. Удаление символов пунктуации (включая кавычки «»—–)
        # Оставляем только буквы, цифры и одиночные пробелы
        t = re.sub(r'[!"#$%&\'()*+,\-./:;<=>?@\\\[\]^_`{|}~«»—–’“”]', " ", t)

        # 5. Схлопывание повторных пробелов в один
        t = re.sub(r"\s+", " ", t).strip()

        return t
