#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""notebook.py: Contains different wrapper for variant caller."""

from pathlib import Path
from typing import List
import nbformat as nbf
import pypipegraph as ppg

__author__ = "Marco Mernberger"
__copyright__ = "Copyright (c) 2020 Marco Mernberger"
__license__ = "mit"


class Cell():
    """
    A cell object wrapping a jupyter notebook cell to be written to a .ipynb
    file.

    During report generation, Cell objects will be collected in order and
    written to a jupyter notebook output file.

    Parameters
    ----------
    text : str
        The content of the cell.
    celltype : str, optional
        The type of the cell, by default "markdown". May be any of ["code", "markdown"].

    Raises
    ------
    ValueError
        If the specified cell type is not allowed.
    """
    def __init__(self, text: str, celltype: str = "markdown"):
        self.text = text
        if celltype not in ["markdown", "code"]:
            raise ValueError(f"Cell type must be any of [markdown, code], was {celltype}.")
        self.type = celltype
        self.__hash = (self.text+self.type).__hash__()

    @property
    def hash(self):
        return self.__hash


class NB():
    """
    A class wrapping a jupyter notebook.

    This class is used to collect cells in a specific order and output them
    to a .ipynb file.

    Parameters
    ----------
    name : str
        Name of the notebook and the resulting file stem.
    path_to_directory : Path, optional
        Output path where to put the file, by default None.
    """
    def __init__(self, name: str, path_to_directory: Path = None):
        self.name = name
        self.result_dir = path_to_directory
        if self.result_dir is None:
            self.result_dir = Path("out") / "notebooks"
        self.result_dir.mkdir(exist_ok=True, parents=True)
        self.path_to_file = self.result_dir / f"{self.name}.ipynb"
        self.ordered_cell_list: List[Cell] = []
        self.nb = nbf.v4.new_notebook()
        self.dependencies = [ppg.FunctionInvariant(str(self.path_to_file) + "_rfunc", self.register_plot)]
        self.invariant: List[str] = []
        self.import_handling()

    def import_handling(self):
        text = """\
from IPython.display import Image
"""
        first = Cell(text, celltype="code")
        self.ordered_cell_list.append(first)
        self.invariant.append(first.hash)

    def register_plot(self, job, text=None):
        if text is None:
            text = f"Result from : {job.job_id}"
        md_cell = Cell(text, "markdown")
        self.ordered_cell_list.append(md_cell)
        pre = "/".join([".."]*(len(self.result_dir.parents)))
        filenames = [pre+"/"+f for f in job.filenames]
        code = f"""\
for filename in {filenames}:
    display(Image(filename))
"""
        code_cell = Cell(code, "code")
        self.ordered_cell_list.append(code_cell)
        self.invariant.extend([md_cell.hash, code_cell.hash])
        self.dependencies.extend(job)

    def commit(self):
        self.nb['cells'] = []
        for cell in self.ordered_cell_list:
            if cell.type == "markdown":
                self.nb['cells'].append(nbf.v4.new_markdown_cell(cell.text))
            else:
                self.nb['cells'].append(nbf.v4.new_code_cell(cell.text))
        self.dependencies.append(ppg.ParameterInvariant(self.name + "__hash", self.invariant))

    def write(self):
        def do_write():
            self.commit()
            with self.path_to_file.open("w") as outp:
                nbf.write(self.nb, outp)
        return ppg.FileGeneratingJob(self.path_to_file, do_write).depends_on(self.dependencies)