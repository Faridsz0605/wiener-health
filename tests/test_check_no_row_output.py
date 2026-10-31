from tools.check_no_row_output import main, violations


def test_flags_row_output_calls():
    src = "df.show()\ndisplay(df)\nprint(row)\n# print(x) in a comment is fine\nlog.info('ok')\n"
    assert violations(src) == [1, 2, 3]


def test_main_scans_tree(tmp_path):
    (tmp_path / "ok.py").write_text("x = 1\n")
    assert main(str(tmp_path)) == 0
    (tmp_path / "job").mkdir()
    (tmp_path / "job" / "bad.py").write_text("df.show(5)\n")
    assert main(str(tmp_path)) == 1
