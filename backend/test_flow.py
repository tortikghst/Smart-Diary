import asyncio
import httpx

BASE_URL = "http://localhost:8080/api/v1"


async def test_smart_diary_flow():
    async with httpx.AsyncClient(timeout=10.0) as client:
        print("🚀 [START] Запуск сквозного тестирования «Умного дневника»...\n")

        # =====================================================================
        # ШАГ 1: Авторизация Демо-Пользователей (Страница 4 Контракта)
        # =====================================================================
        print("🔐 Шаг 1: Авторизация через мок-данные мессенджера MAX...")

        # Вход Учителя
        # Вход Учителя
        teacher_auth = await client.post(
            f"{BASE_URL}/auth/login", json={"initData": "teacher"}
        )

        # ДОБАВЬТЕ ЭТУ СТРОКУ ДЛЯ ДИАГНОСТИКИ:
        print(
            f"  [DEBUG] Статус-код бэкенда: {teacher_auth.status_code}, Ответ: {teacher_auth.text}"
        )

        assert teacher_auth.status_code == 200, "Ошибка входа учителя"
        teacher_token = teacher_auth.json()["access_token"]
        teacher_headers = {"Authorization": f"Bearer {teacher_token}"}
        print("  ✅ Учитель успешно вошел в систему.")

        # Вход Ученика
        student_auth = await client.post(
            f"{BASE_URL}/auth/login", json={"initData": "student"}
        )
        assert student_auth.status_code == 200, "Ошибка входа ученика"
        student_token = student_auth.json()["access_token"]
        student_headers = {"Authorization": f"Bearer {student_token}"}
        print("  ✅ Ученик успешно вошел в систему.\n")

        # =====================================================================
        # ШАГ 2: Проверка профиля учителя (Страница 4 Контракта)
        # =====================================================================
        print("👤 Шаг 2: Запрос профиля учителя /users/me...")
        profile_res = await client.get(f"{BASE_URL}/users/me", headers=teacher_headers)
        assert profile_res.status_code == 200, "Ошибка получения профиля"
        profile_data = profile_res.json()
        assert "subject" in profile_data, "В профиле отсутствует объект subject"
        print(
            f"  ✅ Учитель: {profile_data['full_name']}. Предмет: {profile_data['subject']['name']}\n"
        )

        # =====================================================================
        # ШАГ 3: Умная генерация рассадки (Страница 7 Контракта)
        # =====================================================================
        print("🪑 Шаг 3: Алгоритмический расчет рассадки класса 7А...")
        # Вызываем POST /generate, проверяющий привязку учителя к классу и теги 152-ФЗ
        seating_res = await client.post(
            f"{BASE_URL}/seating/7/generate", headers=teacher_headers
        )
        assert seating_res.status_code == 200, "Ошибка генерации рассадки"
        seating_data = seating_res.json()
        assert (
            seating_data["teacher_position"] == "front_center"
        ), "Неверно рассчитана позиция учителя"
        print(
            f"  ✅ Рассадка успешно построена. Посажено мест в сетку: {len(seating_data['layout_json']['seats'])}\n"
        )

        # =====================================================================
        # ШАГ 4: Главный экран Ученика (Страница 9 Контракта)
        # =====================================================================
        print("👦 Шаг 4: Сборка главного дашборда ученика...")
        student_dash_res = await client.get(
            f"{BASE_URL}/student/dashboard", headers=student_headers
        )
        assert student_dash_res.status_code == 200, "Ошибка дашборда ученика"
        dash_data = student_dash_res.json()
        print(
            f"  ✅ Доступно предметов для листания отчетов: {len(dash_data['subjects'])}"
        )
        print(
            f"  ✅ Количество горящих задолжностей («Огоньков»): {dash_data['debts_count']}"
        )
        print(
            f"  ✅ Текущий лучший стрик выполнения ДЗ: {dash_data['streak']['current_streak']}\n"
        )

        # =====================================================================
        # ШАГ 5: Экспорт высококачественной рассадки PNG в make_one (Страница 8)
        # =====================================================================
        # =====================================================================
        # ШАГ 5: Экспорт высококачественной рассадки PNG в make_one (Страница 8)
        # =====================================================================
        print(
            "🖼️ Шаг 5: Сохранение и проверка динамического экспорта карты рассадки в PNG..."
        )

        # ДОБАВЛЕНО: Сначала сохраняем сгенерированную на Шаге 3 рассадку в базу данных через PUT
        save_seating_res = await client.put(
            f"{BASE_URL}/seating/7",
            json={"layout_json": seating_data["layout_json"]},
            headers=teacher_headers,
        )
        assert (
            save_seating_res.status_code == 200
        ), "Ошибка сохранения рассадки перед скачиванием"
        print("  ✅ Рассадка успешно зафиксирована в СУБД через PUT.")

        # Теперь скачивание PNG отработает без ошибок, так как запись появилась в СУБД
        png_res = await client.get(
            f"{BASE_URL}/seating/7/download", headers=teacher_headers
        )
        assert (
            png_res.status_code == 200
        ), f"Ошибка скачивания PNG. Статус: {png_res.status_code}"
        assert (
            png_res.headers["content-type"] == "image/png"
        ), "Бэкенд вернул не PNG формат"
        print(
            f"  ✅ Изображение рассадки успешно сгенерировано Pillow и отдано бинарным потоком ({len(png_res.content)} байт).\n"
        )

        print(
            "🎉 [SUCCESS] Все критические P0-P1 ручки контракта v0.2 работают идеально!"
        )


if __name__ == "__main__":
    # Запуск асинхронного цикла тестирования
    asyncio.run(test_smart_diary_flow())
