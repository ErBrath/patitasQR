"""Actualizar CHECK rol: agrega admin

Revision ID: 912e48b9e4b8
Revises: ac09532daf33
Create Date: 2025-09-09 16:23:15.706321
"""
from alembic import op

revision = '912e48b9e4b8'
down_revision = 'ac09532daf33'
branch_labels = None
depends_on = None

def upgrade():
    op.drop_constraint('usuario_rol_chk', 'usuario', type_='check')
    op.create_check_constraint(
        'usuario_rol_chk', 'usuario',
        "rol IN ('admin','veterinario','asistente')"
    )

def downgrade():
    op.drop_constraint('usuario_rol_chk', 'usuario', type_='check')
    op.create_check_constraint(
        'usuario_rol_chk', 'usuario',
        "rol IN ('veterinario','asistente')"
    )

