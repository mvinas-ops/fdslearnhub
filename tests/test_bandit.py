import subprocess


def test_bandit_security_scan():
    result = subprocess.run(
        ["bandit", "-r", "app/", "-ll"],
        capture_output=True,
        text=True
    )

    print(result.stdout)

    # Fail test if Bandit finds HIGH/medium issues
    assert result.returncode == 0, "Bandit found security issues"