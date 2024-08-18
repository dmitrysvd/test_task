from uuid import uuid4

import aiofiles
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import get_settings
from db import SessionLocal, UploadedFile
from models import UploadedFileModel
from utils import get_file_path_by_uid, save_file_metadata, upload_file_to_cloud
from loguru import logger


logger.add(get_settings().LOGS_DIR / 'app.log')


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()


@app.post('/files/upload', response_model=UploadedFileModel)
async def upload_file(
    upload_file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Выполнить подгрузку файла."""
    uid = str(uuid4())
    logger.info('Начата загрузка файла {uid}', uid=uid)
    content = await upload_file.read()
    path = get_file_path_by_uid(uid)
    path.write_bytes(content)

    uploaded_file = save_file_metadata(
        uid,
        filename=upload_file.filename or '',
        db=db,
        format=upload_file.content_type,
    )
    logger.info('Файл и метаданные сохранены {uid}', uid=uid)
    background_tasks.add_task(upload_file_to_cloud, path, uid)
    return uploaded_file


@app.post(
    '/files/stream_upload',
    response_model=UploadedFileModel,
)
async def stream_upload_file(
    upload_file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Выполнить потоковую подгрузку файла."""
    uid = str(uuid4())
    logger.info('Начата потоковая загрузка файла {uid}', uid=uid)
    path = get_file_path_by_uid(uid)
    async with aiofiles.open(path, 'wb') as f:
        while chunk := await upload_file.read(1024 * 1024):
            await f.write(chunk)

    uploaded_file = save_file_metadata(
        uid,
        filename=upload_file.filename or '',
        db=db,
        format=upload_file.content_type,
    )
    logger.info('Файл и метаданные сохранены {uid}', uid=uid)
    background_tasks.add_task(upload_file_to_cloud, path, uid)
    return uploaded_file


@app.get('/files', response_model=list[UploadedFileModel])
def list_files(db: Session = Depends(get_db)):
    """Получить список загруженных файлов."""
    return db.scalars(select(UploadedFile)).all()


@app.get('/files/{file_uid}', response_model=UploadedFileModel)
async def get_file(file_uid: str, db: Session = Depends(get_db)):
    """Получить информацию о файле."""
    uploaded_file = db.scalars(
        select(UploadedFile).filter_by(uid=file_uid)
    ).one_or_none()
    if not uploaded_file:
        raise HTTPException(404)
    return uploaded_file


@app.get('/files/{file_uid}/download', response_class=FileResponse)
async def download_file(
    file_uid: str,
    db: Session = Depends(get_db),
):
    """Скачать файл."""
    uploaded_file = db.scalars(
        select(UploadedFile).where(UploadedFile.uid == file_uid)
    ).one_or_none()
    if not uploaded_file:
        raise HTTPException(404)
    file_path = get_settings().FILES_DIR / str(file_uid)
    file_full_name = uploaded_file.original_name + uploaded_file.extension
    return FileResponse(file_path, filename=file_full_name)
