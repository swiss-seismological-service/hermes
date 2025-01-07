# Generic single-database configuration.

Two branches are configured:
- `schema`: which contains changes to everything tracked inside SQLAlchemy.
- `utils`: which contains changes to functions, triggers and so on.

## Usage
To instantiate, upgrade and run the database you can use the __hermes__ cli:

```bash
# Initialize the database to the latest version.
hermes db init

# Upgrade the database to the latest version if it's not already.
hermes db upgrade

# remove all data, tables and other database objects.
hermes db purge
```

## Migrations
To create a new migration you can use the following command:

```bash
# Create a new migration for the utils branch.
alembic revision --autogenerate -m "your message here" --head=utils@head

# Create a new migration for the schema branch.
alembic revision --autogenerate -m "your message here" --head=schema@head
```

Please be extremely careful to always specify the correct head for the branch you are working on, otherwise you might end up with a migration that is not applied, or erroneously applied in case of a fresh database instantiation.

## Details
On database instantiation, the `schema` branch is directly set to the latest version, without executing any migration. This is because the schema branch is supposed to contain only changes to the schema, which are already applied by creating the database using the latest SQLAlchemy models.

The `utils` branch however is applied by running all migrations from the beginning to the latest version. This is because the `utils` branch is supposed to contain changes to functions, triggers and so on, which are not applied by creating the database using the latest SQLAlchemy models.

## Notes
- Names of the database objects created through the `utils` branch should be prefixed with `hermes_` to be picked up correctly and avoid conflicts with other objects.