# latexmk configuration — LuaLaTeX + biber, build products in paper/build/
$pdf_mode = 4;             # lualatex
$lualatex = 'lualatex -interaction=nonstopmode -halt-on-error -file-line-error %O %S';
$out_dir = 'build';
$bibtex_use = 2;           # run biber, delete .bbl on clean
$max_repeat = 6;
