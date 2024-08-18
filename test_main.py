from uuid import uuid4
import pytest
from pathlib import Path
from main import app, get_db
from fastapi.testclient import TestClient
import io
from config import Settings
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from db import Base, UploadedFile

client = TestClient(app)


@pytest.fixture
def uploaded_file(db, files_dir) -> UploadedFile:
    uid = str(uuid4())
    (files_dir / uid).write_bytes(b'some_content')
    file = UploadedFile(
        uid=uid,
        size=1,
        format='text/html',
        original_name='text',
        extension='txt',
    )
    db.add(file)
    db.commit()
    return file


@pytest.fixture
def files_dir(tmpdir):
    return Path(tmpdir.strpath)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def mocking(files_dir, db, monkeypatch, tmpdir):
    def override_get_settings():
        return Settings(
            FILES_DIR=files_dir,
            LOGS_DIR=tmpdir.strpath,
            CLOUD_API_KEY='test_token',
            DATABASE_URL='sqlite://',
        )

    def override_get_db():
        return db

    def override_upload_to_cloud(*args, **kwargs):
        pass

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr('utils.get_settings', override_get_settings)
    monkeypatch.setattr('main.get_settings', override_get_settings)
    monkeypatch.setattr('db.get_settings', override_get_settings)
    monkeypatch.setattr('main.upload_file_to_cloud', override_upload_to_cloud)


def test_upload_file(files_dir, db):
    """
    Act: Загрузка файла на сервер.
    Assert: Файл загружен на сервер.
    """
    file_content = b'some_content'
    buffer = io.BytesIO(file_content)
    response = client.post(
        '/files/upload',
        files={
            'upload_file': ('text.txt', buffer, 'text/html'),
        },
    )
    assert response.is_success, response.content
    response_data = response.json()
    assert response_data['format'] == 'text/html'
    assert response_data['original_name'] == 'text'
    assert response_data['extension'] == 'txt'
    assert (files_dir / str(response_data['uid'])).exists()
    assert (files_dir / str(response_data['uid'])).read_bytes() == file_content
    assert (
        len(
            db.scalars(
                select(UploadedFile).where(UploadedFile.uid == response_data['uid'])
            ).all()
        )
        == 1
    )


def test_stream_upload_file(files_dir, db):
    """
    Act: Потоковая загрузка файла на сервер.
    Assert: Файл загружен на сервер.
    """
    file_content = b'some_content'
    buffer = io.BytesIO(file_content)
    response = client.post(
        '/files/stream_upload',
        files={
            'upload_file': ('text.txt', buffer, 'text/html'),
        },
    )
    assert response.is_success, response.content
    response_data = response.json()
    assert response_data['format'] == 'text/html'
    assert response_data['original_name'] == 'text'
    assert response_data['extension'] == 'txt'
    assert (files_dir / str(response_data['uid'])).exists()
    assert (files_dir / str(response_data['uid'])).read_bytes() == file_content
    assert (
        len(
            db.scalars(
                select(UploadedFile).where(UploadedFile.uid == response_data['uid'])
            ).all()
        )
        == 1
    )


def test_get_file_metadata(uploaded_file):
    """
    Arrange: На диске есть загруженный файл, в БД есть метаданные.
    Act: Получение метаданных файла.
    Assert: Метаданные получены.
    """
    response = client.get(f'/files/{uploaded_file.uid}')
    assert response.is_success
    response_data = response.json()
    assert response_data['format'] == 'text/html'
    assert response_data['original_name'] == 'text'
    assert response_data['extension'] == 'txt'


def test_download_file(uploaded_file):
    """
    Arrange: На диске есть загруженный файл, в БД есть метаданные.
    Act: Запрос содержимого файла.
    Assert: Файл скачан.
    """
    response = client.get(f'/files/{uploaded_file.uid}/download')
    assert response.is_success
    assert response.content == b'some_content'
