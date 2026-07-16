from testcontainers.postgres import PostgresContainer

with PostgresContainer("postgres:16") as postgres:
    print(postgres.get_connection_url())
