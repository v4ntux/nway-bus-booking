"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transport_companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "cities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("country", sa.String(2), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("first_name", sa.String(100)),
        sa.Column("last_name", sa.String(100)),
        sa.Column("email", sa.String(255)),
        sa.Column("password_hash", sa.String(255)),
        sa.Column("role", sa.Enum("passenger", "driver", "operator", "admin", "superadmin", name="userrole"), nullable=False),
        sa.Column("status", sa.Enum("active", "blocked", name="userstatus"), nullable=False),
        sa.Column("phone_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transport_companies.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_phone", "users", ["phone"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "user_stats",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("completed_trips", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cancelled_reservations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("no_show_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trust_score", sa.Integer(), nullable=False, server_default="100"),
    )

    op.create_table(
        "routes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("origin_city_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cities.id"), nullable=False),
        sa.Column("destination_city_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cities.id"), nullable=False),
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("distance_km", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transport_companies.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", "origin_city_id", "destination_city_id"),
    )
    op.create_index("ix_routes_origin_city_id", "routes", ["origin_city_id"])
    op.create_index("ix_routes_destination_city_id", "routes", ["destination_city_id"])
    op.create_index("ix_routes_company_id", "routes", ["company_id"])

    op.create_table(
        "route_stops",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("route_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("routes.id"), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cities.id"), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("arrival_offset_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("departure_offset_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("route_id", "order_index"),
    )
    op.create_index("ix_route_stops_route_id", "route_stops", ["route_id"])

    op.create_table(
        "buses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transport_companies.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("registration_number", sa.String(32), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("seat_count", sa.Integer(), nullable=False),
        sa.Column("layout_type", sa.String(32), nullable=False, server_default="2+2"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_buses_company_id", "buses", ["company_id"])

    seattype = sa.Enum("standard", "premium", "child", "accessibility", "blocked", name="seattype")
    celltype = sa.Enum(
        "seat", "aisle", "driver", "door", "stairs", "toilet", "empty", "service", name="layoutcelltype"
    )
    seattype.create(op.get_bind(), checkfirst=True)
    celltype.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "seats",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bus_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("buses.id"), nullable=False),
        sa.Column("seat_number", sa.String(16), nullable=False),
        sa.Column("row", sa.Integer(), nullable=False),
        sa.Column("column", sa.Integer(), nullable=False),
        sa.Column("type", postgresql.ENUM("standard", "premium", "child", "accessibility", "blocked", name="seattype", create_type=False), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_accessibility", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_child", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_premium", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_seats_bus_id", "seats", ["bus_id"])

    op.create_table(
        "bus_layouts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bus_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("buses.id"), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False, server_default="Default"),
        sa.Column("rows", sa.Integer(), nullable=False),
        sa.Column("columns", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "layout_cells",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("layout_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bus_layouts.id"), nullable=False),
        sa.Column("row", sa.Integer(), nullable=False),
        sa.Column("column", sa.Integer(), nullable=False),
        sa.Column("cell_type", postgresql.ENUM("seat", "aisle", "driver", "door", "stairs", "toilet", "empty", "service", name="layoutcelltype", create_type=False), nullable=False),
        sa.Column("seat_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("seats.id")),
        sa.Column("x", sa.Integer()),
        sa.Column("y", sa.Integer()),
        sa.CheckConstraint('"row" >= 0 AND "column" >= 0', name="ck_layout_cell_nonneg"),
    )
    op.create_index("ix_layout_cells_layout_id", "layout_cells", ["layout_id"])

    tripstatus = sa.Enum("draft", "scheduled", "boarding", "departed", "completed", "cancelled", name="tripstatus")
    tripstatus.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "trips",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("route_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("routes.id"), nullable=False),
        sa.Column("bus_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("buses.id"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transport_companies.id"), nullable=False),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("departure_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estimated_arrival_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", postgresql.ENUM("draft", "scheduled", "boarding", "departed", "completed", "cancelled", name="tripstatus", create_type=False), nullable=False),
        sa.Column("base_price_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("boarding_location", sa.String(255)),
        sa.Column("destination_location", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_trips_route_id", "trips", ["route_id"])
    op.create_index("ix_trips_company_id", "trips", ["company_id"])
    op.create_index("ix_trips_departure", "trips", ["departure_datetime"])
    op.create_index("ix_trips_route_departure", "trips", ["route_id", "departure_datetime"])
    op.create_index("ix_trips_company_status", "trips", ["company_id", "status"])

    res_status = sa.Enum(
        "pending",
        "awaiting_deposit",
        "awaiting_admin_approval",
        "confirmed",
        "cancelled",
        "expired",
        "completed",
        "no_show",
        name="reservationstatus",
    )
    pay_status = sa.Enum(
        "unpaid", "pending", "partially_paid", "paid", "refunded", "failed", name="paymentstatus"
    )
    pay_method = sa.Enum("online", "cash", "transfer", "deposit", "other", name="paymentmethod")
    res_status.create(op.get_bind(), checkfirst=True)
    pay_status.create(op.get_bind(), checkfirst=True)
    pay_method.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "reservations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("trip_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trips.id"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transport_companies.id"), nullable=False),
        sa.Column("public_code", sa.String(16), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "awaiting_deposit",
                "awaiting_admin_approval",
                "confirmed",
                "cancelled",
                "expired",
                "completed",
                "no_show",
                name="reservationstatus",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "payment_status",
            postgresql.ENUM("unpaid", "pending", "partially_paid", "paid", "refunded", "failed", name="paymentstatus", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "payment_method",
            postgresql.ENUM("online", "cash", "transfer", "deposit", "other", name="paymentmethod", create_type=False),
        ),
        sa.Column("total_amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("contact_phone", sa.String(32), nullable=False),
        sa.Column("deposit_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deposit_received", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_reservations_public_code", "reservations", ["public_code"], unique=True)
    op.create_index("ix_reservations_contact_phone", "reservations", ["contact_phone"])
    op.create_index("ix_reservations_status", "reservations", ["status"])
    op.create_index("ix_reservations_trip_status", "reservations", ["trip_id", "status"])
    op.create_index("ix_reservations_company", "reservations", ["company_id"])
    op.create_index("ix_reservations_user_id", "reservations", ["user_id"])
    op.create_index("ix_reservations_trip_id", "reservations", ["trip_id"])

    op.create_table(
        "reservation_seats",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("reservation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reservations.id"), nullable=False),
        sa.Column("trip_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trips.id"), nullable=False),
        sa.Column("seat_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("seats.id"), nullable=False),
        sa.Column("price_minor", sa.Integer(), nullable=False),
        sa.Column("is_active_hold", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index("ix_reservation_seats_reservation", "reservation_seats", ["reservation_id"])
    op.create_index(
        "uq_active_trip_seat",
        "reservation_seats",
        ["trip_id", "seat_id"],
        unique=True,
        postgresql_where=sa.text("is_active_hold = true"),
    )

    op.create_table(
        "reservation_passengers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("reservation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reservations.id"), nullable=False),
        sa.Column("seat_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("seats.id"), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100)),
        sa.Column("phone", sa.String(32)),
        sa.Column("document_type", sa.String(32)),
        sa.Column("document_number", sa.String(64)),
        sa.Column("date_of_birth", sa.DateTime(timezone=True)),
        sa.Column("gender", sa.String(16)),
        sa.Column("nationality", sa.String(2)),
    )
    op.create_index("ix_reservation_passengers_reservation_id", "reservation_passengers", ["reservation_id"])

    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("reservation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reservations.id"), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column(
            "method",
            postgresql.ENUM("online", "cash", "transfer", "deposit", "other", name="paymentmethod", create_type=False),
            nullable=False,
        ),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("unpaid", "pending", "partially_paid", "paid", "refunded", "failed", name="paymentstatus", create_type=False),
            nullable=False,
        ),
        sa.Column("provider_payment_id", sa.String(128)),
        sa.Column("extra_data", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_payments_reservation_id", "payments", ["reservation_id"])

    ticketstatus = sa.Enum("valid", "used", "cancelled", name="ticketstatus")
    ticketstatus.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("public_id", sa.String(20), nullable=False),
        sa.Column("qr_token", sa.String(64), nullable=False),
        sa.Column("reservation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reservations.id"), nullable=False),
        sa.Column("passenger_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reservation_passengers.id"), nullable=False),
        sa.Column("trip_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trips.id"), nullable=False),
        sa.Column("seat_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("seats.id"), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("valid", "used", "cancelled", name="ticketstatus", create_type=False),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tickets_public_id", "tickets", ["public_id"], unique=True)
    op.create_index("ix_tickets_qr_token", "tickets", ["qr_token"], unique=True)
    op.create_index("ix_tickets_reservation_id", "tickets", ["reservation_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("before_data", postgresql.JSONB()),
        sa.Column("after_data", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])

    op.create_table(
        "otp_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("code_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_otp_challenges_phone", "otp_challenges", ["phone"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_table("otp_challenges")
    op.drop_table("audit_logs")
    op.drop_table("tickets")
    op.drop_table("payments")
    op.drop_table("reservation_passengers")
    op.drop_table("reservation_seats")
    op.drop_table("reservations")
    op.drop_table("trips")
    op.drop_table("layout_cells")
    op.drop_table("bus_layouts")
    op.drop_table("seats")
    op.drop_table("buses")
    op.drop_table("route_stops")
    op.drop_table("routes")
    op.drop_table("user_stats")
    op.drop_table("users")
    op.drop_table("cities")
    op.drop_table("transport_companies")
    sa.Enum(name="ticketstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="paymentmethod").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="paymentstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="reservationstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="tripstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="layoutcelltype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="seattype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="userstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
