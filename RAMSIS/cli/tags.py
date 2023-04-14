import typer 
from prefect.client import get_client

app = typer.Typer()

async def set_concurrency_limit(tag, limit):
    with get_client() as client:
        limit_id = await client.create_concurrency_limit(
            tag=tag, 
            concurrency_limit=limit
            )


async def delete_concurrency_limit(tag):
    with get_client() as client:
        await client.delete_concurrency_limit_by_tag(tag=tag)


async def read_concurrency_limit(tag):
    with get_client() as client:
        limit = await client.read_concurrency_limit_by_tag(tag="small_instance")
        return limit


@app.command()
def set(tag: str, limit: int):
    await set_concurrency_limit(tag, limit)
    typer.echo("Tag has been set with limit")

@app.command()
def delete(tag: str):
    await delete_concurrency_limit(tag)
    typer.echo("Tag has been deleted")

@app.command()
def read(tag: str):
    limit = await read_concurrency_limit(tag)
    typer.echo(f"Tag concurrency limit is: {limit}")
