from config import get_settings
from uuid import UUID, uuid4
from sqlalchemy import create_engine, Uuid, String
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UploadedFile(Base):
    __tablename__ = 'uploaded_file'

    uid: Mapped[str] = mapped_column(String(), primary_key=True, default=uuid4)
    size: Mapped[int] = mapped_column()
    format: Mapped[str] = mapped_column(String(200))
    original_name: Mapped[str] = mapped_column(String(1000))
    extension: Mapped[str] = mapped_column(String(10))
    is_uploaded_to_cloud: Mapped[bool] = mapped_column(default=False)


connect_args = (
    {"check_same_thread": False}
    if str(get_settings().DATABASE_URL).startswith('sqlite')
    else None
)

engine = create_engine(
    str(get_settings().DATABASE_URL),
    echo=get_settings().IS_DEBUG,
    **({'connect_args': connect_args} if connect_args else {})
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)
