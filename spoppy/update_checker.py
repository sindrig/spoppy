import requests
import subprocess


def pause_for_effect():
    # Pause execution so the user sees what happened
    try:
        raw_input()
    except NameError:
        input()


def parse_version(v):
    try:
        return [int(part) for part in v.split('.')]
    except ValueError:
        return [0, 0, 0]


def check_for_updates(click, version, lock):
    info = requests.get(
        "https://pypi.python.org/pypi/spoppy/json").json()["info"]

    pypi_version = info["version"]

    version = version

    if parse_version(version) < parse_version(pypi_version):
        click.echo("\033[1m\033[94mA new version of spoppy is "
                   "available!\033[0m")
        click.echo("\033[1m\033[96m Installed: {} \033[92m"
                   "PyPi: {}\033[0m".format(version,
                                            pypi_version))
        click.echo("\033[94m You can install it yourself or "
                   "automatically download it. Automatically "
                   "install it?\033[0m")

        message = '[Y(Automatically) / n(Manually)] '
        try:
            response = raw_input(message).lower()
        except NameError:
            response = input(message).lower()

        # Only do anything if they say yes
        if response == "y":
            try:
                subprocess.check_call([
                    "sudo", "pip", "install", "spoppy",
                    "--upgrade", "--no-cache-dir"
                ])
                click.echo(
                    "\033[1m\033[92mspoppy updated sucessfully!\033[0m")

                click.echo("Please restart spoppy!")
                lock.release()
                pause_for_effect()

                raise SystemExit

            except subprocess.CalledProcessError:
                # Pip failed to automatically update
                click.echo(
                    "\033[1m\033[91mAutomatic updating failed!\033[0m")
                click.echo(
                    "You will have to manually update spoppy")
                pause_for_effect()
