from collapse_lab.demo import main


def test_demo_runs(capsys):
    assert main(["--quick"]) == 0
    out = capsys.readouterr().out
    assert "1-D Gaussian" in out and "Categorical" in out and "Linear regression" in out
