# Open Data Linter

このリポジトリは、総務省が発表している「[統計表における機械判読可能なデータの表記方法の統一ルールの策定](https://www.soumu.go.jp/menu_news/s-news/01toukatsu01_02000186.html)」に基づき、ファイルがそのルールに則しているかを判定するロジックを記述しています。

ドキュメントは[こちら](https://volare-all.github.io/open-data-linter-docs/) です。

issue, pull request お待ちしています。

## how to install

```bash
pip install git+https://github.com/volare-all/open-data-linter.git
```

## how to use

```python
from opendatalinter import OpenDataLinter

file_path = "/path/to/your/file"
with open(file_path, "rb") as f:
    data = f.read()

linter = OpenDataLinter(data, file_path)
res = linter.check_1_1()  # return LintResult, see vo.py
print(res.is_valid)
print(res.invalid_contents)
```
