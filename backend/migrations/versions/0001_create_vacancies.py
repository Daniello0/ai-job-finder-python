from alembic import op


revision = "0001_create_vacancies"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute(
        """
        CREATE TABLE vacancies (
            id SERIAL PRIMARY KEY,
            title VARCHAR(512) NOT NULL,
            company VARCHAR(512) NOT NULL,
            salary VARCHAR(256) NOT NULL,
            payment_frequency VARCHAR(128) NOT NULL,
            experience VARCHAR(256) NOT NULL,
            employment VARCHAR(256) NOT NULL,
            hiring_format VARCHAR(256) NOT NULL,
            schedule VARCHAR(256) NOT NULL,
            hours VARCHAR(256) NOT NULL,
            work_format VARCHAR(256) NOT NULL,
            skills TEXT NOT NULL,
            url VARCHAR(2048) NOT NULL,
            description TEXT NOT NULL,
            embedding vector(384),
            CONSTRAINT uq_vacancies_url UNIQUE (url)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS vacancies")

