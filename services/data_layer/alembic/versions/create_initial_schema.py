"""Create initial schema

Revision ID: 60b4b64a29fa
Revises: 
Create Date: 2024-02-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '60b4b64a29fa'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Articles table
    op.create_table('articles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.String(length=255), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('publication_date', sa.Date(), nullable=False),
        sa.Column('abstract_text', sa.Text(), nullable=True),
        sa.Column('s3_abstract_path', sa.String(length=512), nullable=True),
        sa.Column('s3_fulltext_path', sa.String(length=512), nullable=True),
        sa.Column('url', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source', 'source_id')
    )
    
    # Authors table
    op.create_table('authors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Organizations table
    op.create_table('organizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('country', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Categories table
    op.create_table('categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['categories.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    
    # Newsletters table
    op.create_table('newsletters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('issue_date', sa.Date(), nullable=False),
        sa.Column('s3_path', sa.String(length=512), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # ProcessingEvents table
    op.create_table('processing_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(length=255), nullable=False),
        sa.Column('event_timestamp', sa.DateTime(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('source_job_id', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Emails table
    op.create_table('emails',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('newsletter_id', sa.Integer(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('recipient_count', sa.Integer(), nullable=True),
        sa.Column('s3_path', sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(['newsletter_id'], ['newsletters.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Article-Authors association table
    op.create_table('article_authors',
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('author_order', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ),
        sa.ForeignKeyConstraint(['author_id'], ['authors.id'], ),
        sa.PrimaryKeyConstraint('article_id', 'author_id')
    )
    
    # Article-Categories association table
    op.create_table('article_categories',
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
        sa.PrimaryKeyConstraint('article_id', 'category_id')
    )
    
    # Author-Organizations association table
    op.create_table('author_organizations',
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['authors.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('author_id', 'organization_id')
    )
    
    # Newsletter-Articles association table
    op.create_table('newsletter_articles',
        sa.Column('newsletter_id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('section', sa.String(length=255), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ),
        sa.ForeignKeyConstraint(['newsletter_id'], ['newsletters.id'], ),
        sa.PrimaryKeyConstraint('newsletter_id', 'article_id')
    )
    
    # Create indexes for improved query performance
    op.create_index(op.f('ix_articles_publication_date'), 'articles', ['publication_date'], unique=False)
    op.create_index(op.f('ix_articles_source'), 'articles', ['source'], unique=False)
    op.create_index(op.f('ix_authors_name'), 'authors', ['name'], unique=False)
    op.create_index(op.f('ix_categories_code'), 'categories', ['code'], unique=True)
    op.create_index(op.f('ix_newsletters_issue_date'), 'newsletters', ['issue_date'], unique=False)
    op.create_index(op.f('ix_processing_events_event_type'), 'processing_events', ['event_type'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order (respect foreign key constraints)
    op.drop_table('newsletter_articles')
    op.drop_table('author_organizations')
    op.drop_table('article_categories')
    op.drop_table('article_authors')
    op.drop_table('emails')
    op.drop_table('processing_events')
    op.drop_table('newsletters')
    op.drop_table('categories')
    op.drop_table('organizations')
    op.drop_table('authors')
    op.drop_table('articles') 