import requests
import subprocess


def check_for_updates(click, version, lock):
    info = requests.get(
        "https://pypi.python.org/pypi/spoppy/json").json()["info"]

    pypi_version = info["version"]

    version = version

    if version < pypi_version:
        click.echo("\033[1m\033[94mA new version of spoppy is "
                   "available!\033[0m")
        click.echo("\033[1m\033[96m Installed: {} \033[92m"
                   "PyPi: {}\033[0m".format(version,
                                            pypi_version))
        click.echo("\033[94m You can install it yourself or "
                   "automatically download it. Automatically "
                   "install it?\033[0m")
        try:
            response = raw_input(
                '[Y(Automatically) / n(Manually)] ').lower()
        except NameError:
            response = input(
                '[Y(Automatically) / n(Manually)] ').lower()

        # Only do anything if they say yes
        if response == "y":
            try:
                subprocess.check_call(
                    ["sudo", "pip", "install", "spoppy", "--upgrade"])
                click.echo(
                    "\033[1m\033[92mspoppy updated sucessfully!\033[0m")

                click.echo("Please restart spoppy!")
                lock.release()
                raise SystemExit

            except subprocess.CalledProcessError:
                # Pip failed to automatically update
                click.echo(
                    "\033[1m\033[91mAutomatic updating failed!\033[0m")
                click.echo(
                    "You will have to manually update spoppy")

                # Pause execution so the user sees the error
                try:
                    raw_input()
                except NameError:
                    input()
