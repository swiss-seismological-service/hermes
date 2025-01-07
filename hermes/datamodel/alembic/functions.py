from alembic_utils.pg_function import PGFunction

# !!!!!!!!!!! Signatures need to start with 'hermes_' !!!!!!!!!!!!!

dummy = PGFunction(
    schema='public',
    signature='hermes_dummy()',
    definition="""
  RETURNS void AS $$
  BEGIN
    -- No operation
  END;
  $$ LANGUAGE plpgsql;
  """
)
