import typer

app = typer.Typer()


@app.command(help="Sample command")
def test() -> None:
    print("Hello world")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
