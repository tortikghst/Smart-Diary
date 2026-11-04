import os
from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from scr.database import get_db_session
from scr.repositories.repositorie import UserRepository
from scr.api.auth_deps import require_role
from scr.schemas.seating_schemas import SeatingUpdateRequest, SeatingResponse
from scr.services.image_service import ImageProcessingService
from scr.config import settings
from scr.api.auth_deps_own import check_class_owner
from scr.model.model import StudentMarkerModel, StudentMarker

seating_router = APIRouter(prefix="/seating", tags=["Рассадка Класса"])


@seating_router.post(
    "/{class_id}/generate",
    response_model=SeatingResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_smart_seating_layout(
    class_id: int,
    cols: int = 6,  # <--- Добавили параметр (по умолчанию 6)
    _: None = Depends(check_class_owner),
    current_user: dict = Depends(require_role(["teacher"])),
    db: AsyncSession = Depends(get_db_session),
):
    teacher_id = int(current_user["sub"])
    # Передаем cols в репозиторий
    generated_layout = await UserRepository.generate_smart_seating(
        db=db, class_id=class_id, teacher_id=teacher_id, cols=cols
    )
    if not generated_layout:
        raise HTTPException(status_code=403, detail="Доступ запрещен.")
    if "empty" in generated_layout:
        raise HTTPException(status_code=404, detail="В классе нет учеников.")
    return generated_layout

@seating_router.get(
    "/{class_id}", response_model=SeatingResponse, status_code=status.HTTP_200_OK
)
async def get_seating(
    class_id: int,
    _: None = Depends(check_class_owner),
    current_user: dict = Depends(require_role(["teacher"])),
    db: AsyncSession = Depends(get_db_session),
):
    """Получить текущую сетку рассадки класса."""
    seating_data = await UserRepository.get_seating_with_metadata(
        db=db, class_id=class_id
    )
    if not seating_data:
        raise HTTPException(status_code=404, detail="Рассадка не сгенерирована.")
    return {
        "class_id": seating_data["class_id"],
        "layout_json": seating_data["layout_json"],
        "teacher_position": seating_data["teacher_position"],
        "photo_url": (
            f"/api/v1/seating/{class_id}/photo"
            if seating_data["photo_filename"]
            else None
        ),
    }


@seating_router.put(
    "/{class_id}", response_model=SeatingResponse, status_code=status.HTTP_200_OK
)
async def update_seating(
    class_id: int,
    payload: SeatingUpdateRequest,
    _: None = Depends(check_class_owner),
    current_user: dict = Depends(require_role(["teacher"])),
    db: AsyncSession = Depends(get_db_session),
):
    """Сохранить рассадку и синхронизировать маркеры с БД."""
    layout = payload.layout_json
    teacher_col = layout.teacher.col
    total_cols = (
        layout.grid.cols if hasattr(layout.grid, "cols") else layout.grid.get("cols", 6)
    )

    if teacher_col < total_cols / 3:
        computed_position = "front_left"
    elif teacher_col > (2 * total_cols) / 3:
        computed_position = "front_right"
    else:
        computed_position = "front_center"

    layout_dict = layout.model_dump()

    # 🔥 СИНХРОНИЗАЦИЯ МАРКЕРОВ С БД 🔥
    await db.execute(delete(StudentMarkerModel).where(StudentMarkerModel.class_id == class_id))

    MARKER_MAP = {
        "vision": StudentMarker.FRONT_ROW_PREFERENCE,
        "front_row_preference": StudentMarker.FRONT_ROW_PREFERENCE,
        "hearing": StudentMarker.ACOUSTIC_PREFERENCE,
        "acoustic_preference": StudentMarker.ACOUSTIC_PREFERENCE,
        "behavior": StudentMarker.SEPARATION_REQUIRED,
        "separation_required": StudentMarker.SEPARATION_REQUIRED,
        "separation_requered": StudentMarker.SEPARATION_REQUIRED,
    }

    for seat in layout_dict.get("seats", []):
        sid = seat.get("student_id")
        front_markers = seat.get("markers", [])
        for m_str in front_markers:
            if m_str in MARKER_MAP:
                db.add(StudentMarkerModel(
                    student_id=sid,
                    class_id=class_id,
                    marker=MARKER_MAP[m_str]
                ))
    
    await db.flush()

    seating = await UserRepository.save_class_seating(
        db=db, class_id=class_id, layout=layout_dict, teacher_pos=computed_position
    )

    return {
        "class_id": seating.class_id,
        "layout_json": seating.layout_json,
        "teacher_position": seating.teacher_position,
        "photo_url": (
            f"/api/v1/seating/{class_id}/photo" if seating.photo_filename else None
        ),
    }

@seating_router.get("/{class_id}/download", status_code=status.HTTP_200_OK)
async def download_seating_png(
    class_id: int,
    _: None = Depends(check_class_owner),
    current_user: dict = Depends(require_role(["teacher"])),
    db: AsyncSession = Depends(get_db_session),
):
    """Экспорт схемы рассадки класса в PNG."""
    seating_data = await UserRepository.get_seating_with_metadata(db=db, class_id=class_id)
    if not seating_data:
        raise HTTPException(status_code=404, detail="Рассадка не найдена.")

    png_buffer = ImageProcessingService.generate_seating_png(
        layout_json=seating_data["layout_json"],
        teacher_position=seating_data["teacher_position"],
        class_name=seating_data["class_name"],
    )

    return StreamingResponse(
        png_buffer,
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename=seating_class_{class_id}.png"},
    )

@seating_router.post("/{class_id}/photo", status_code=status.HTTP_200_OK)
async def upload_seating_photo(
    class_id: int,
    _: None = Depends(check_class_owner),
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role(["teacher"])),
    db: AsyncSession = Depends(get_db_session),
):
    """Загрузка реальной фотографии класса."""
    MAX_FILE_SIZE = 5 * 1024 * 1024
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Файл больше 5 МБ.")

    seating = await UserRepository.get_class_seating(db=db, class_id=class_id)
    if not seating:
        raise HTTPException(status_code=404, detail="Сначала создайте сетку.")

    try:
        saved_filename = ImageProcessingService.validate_and_save_photo(
            file_bytes=file_bytes, filename=file.filename, class_id=class_id
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    await UserRepository.update_class_seating_photo(db=db, class_id=class_id, filename=saved_filename)
    await UserRepository.write_audit_log(
        db=db, action="photo.upload", target_type="seating", target_id=str(class_id), actor_id=int(current_user["sub"])
    )
    return {"message": "Фото загружено.", "filename": saved_filename}

@seating_router.get("/{class_id}/photo", status_code=status.HTTP_200_OK)
async def get_seating_photo_file(
    class_id: int,
    _: None = Depends(check_class_owner),
    current_user: dict = Depends(require_role(["teacher"])),
    db: AsyncSession = Depends(get_db_session),
):
    """Отдача фотографии класса с диска."""
    seating = await UserRepository.get_class_seating(db=db, class_id=class_id)
    if not seating or not seating.photo_filename:
        raise HTTPException(status_code=404, detail="Фотография отсутствует.")

    photos_dir = getattr(settings, "PHOTOS_DIR", "/tmp/photos")
    file_path = os.path.join(photos_dir, seating.photo_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл физически удален.")

    return FileResponse(file_path, media_type="image/png")