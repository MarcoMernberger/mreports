#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""notebook.py: Contains different wrapper for variant caller."""

from pathlib import Path
from typing import List, Union
from pypipegraph import Job, FileGeneratingJob, MultiFileGeneratingJob, PlotJob
import nbformat as nbf
import pypipegraph as ppg
import os
import subprocess

__author__ = "Marco Mernberger"
__copyright__ = "Copyright (c) 2020 Marco Mernberger"
__license__ = "mit"


class Cell:
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
    tags: List[str], optional
        Optional list of tags for the cell.

    Raises
    ------
    ValueError
        If the specified cell type is not allowed.
    """

    def __init__(self, text: str, celltype: str = "markdown", tags: List[str] = []):
        self.text = text
        if celltype not in ["markdown", "code"]:
            raise ValueError(
                f"Cell type must be any of [markdown, code], was {celltype}."
            )
        self.type = celltype
        self.tags = tags
        self.meta = {}
        if len(tags) > 0:
            self.meta["tags"] = tags
        self.__hash = (self.text + self.type + "".join(self.tags)).__hash__()

    @property
    def hash(self):
        return self.__hash

    def __str__(self):
        return f"Cell(text={self.text}, celltype={self.type}, tags={self.tags})"


class NB:
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
        self.project_name = Path(os.environ["ANYSNAKE_PROJECT_PATH"]).name
        self.result_dir = path_to_directory
        if self.result_dir is None:
            self.result_dir = Path("out") / "notebooks"
        self.result_dir.mkdir(exist_ok=True, parents=True)
        self.path_to_file = self.result_dir / f"{self.name}_{self.project_name}.ipynb"
        self.ordered_cell_list: List[Cell] = []
        self.nb = nbf.v4.new_notebook()
        self.dependencies = [
            ppg.FunctionInvariant(
                str(self.path_to_file) + "_rfunc", self.register_plot
            ),
            ppg.FunctionInvariant(
                str(self.path_to_file) + "_rtextfunc", self.register_text
            ),
            ppg.FunctionInvariant(
                str(self.path_to_file) + "_rhtmlfunc", self.register_html
            ),

            ppg.FunctionInvariant(str(self.path_to_file) + "_commitfunc", self.commit),
        ]
        self.invariant: List[str] = []
        self.colors = ["green", "blue", "orange", "red"]
        self.section_index = 0
        self.init_first_cell()

    def get_color_tag(self):
        index = self.section_index % len(self.colors)
        return self.colors[index]

    def new_section(self):
        self.section_index += 1

    def init_first_cell(self):
        text = """\
from IPython.display import Image
from IPython.display import HTML
"""
        first = Cell(text, celltype="code")
        text = f"""\
## Analysis report for
## {Path(os.environ["ANYSNAKE_PROJECT_PATH"]).name}. 
        """
        second = Cell(text, celltype="markdown")
        self.ordered_cell_list.extend([first, second])
        self.invariant.append([first.hash, second.hash])

    def register_plot(self, job: PlotJob, text: str = None):
        tags = [self.get_color_tag()]
        if text is None:
            text = f"Result from : {job.job_id}"
        md_cell = Cell(f"#### {text}:", "markdown")
        self.ordered_cell_list.append(md_cell)
        filenames = [os.path.relpath(Path(f).resolve(), self.result_dir) for f in job.filenames if f.endswith(".png")]
        code = f"""\
for filename in {filenames}:
    display(Image(filename, embed=True, retina=True))
"""
        code_cell = Cell(code, "code", tags)
        self.ordered_cell_list.append(code_cell)
        self.invariant.extend([md_cell.hash, code_cell.hash])
        self.dependencies.extend(job)

    def register_text(self, text: str):
        tags = [self.get_color_tag()]
        md_cell = Cell(f"### **{text}**:", "markdown", tags)
        self.ordered_cell_list.append(md_cell)
        self.invariant.append(md_cell.hash)

    def register_html(self, filename: Path, job, text: str = None):
        tags = [self.get_color_tag()]
        if text is None:
            text = f"HTML from : {filename}"
        md_cell = Cell(f"#### {text}:", "markdown")
        self.ordered_cell_list.append(md_cell)
        rel_filename = os.path.relpath(Path(filename).resolve(), self.result_dir)
        code = f'HTML(filename="{rel_filename}")'
        code_cell = Cell(code, "code", tags)
        self.ordered_cell_list.append(code_cell)
        self.invariant.extend([md_cell.hash, code_cell.hash])
        self.dependencies.extend(job)

    def register_file(
        self,
        job: Union[FileGeneratingJob, MultiFileGeneratingJob],
        text: str,
        index: int = None,
    ):
        tags = [self.get_color_tag()]
        if isinstance(job, FileGeneratingJob):
            if text is None:
                text = f"File {job.job_id}"
            md_cell = Cell(f"### **{text}**:", "markdown", tags)
            self.ordered_cell_list.append(md_cell)
            self.invariant.append(md_cell.hash)

    def commit(self):
        self.nb["cells"] = []
        for cell in self.ordered_cell_list:
            if cell.type == "markdown":
                self.nb["cells"].append(
                    nbf.v4.new_markdown_cell(cell.text, metadata=cell.meta)
                )
            else:
                self.nb["cells"].append(
                    nbf.v4.new_code_cell(cell.text, metadata=cell.meta)
                )
        self.dependencies.append(
            ppg.ParameterInvariant(self.name + "__hash", self.invariant)
        )

    def write(self):
        def do_write():
            self.commit()
            with self.path_to_file.open("w") as outp:
                nbf.write(self.nb, outp)

        return ppg.FileGeneratingJob(self.path_to_file, do_write).depends_on(
            self.dependencies
        )  # .depends_on(ppg.ParameterInvariant(self.name + "__hash", self.invariant))

    def convert(self, to: str = "html"):
        outfile = self.path_to_file.with_suffix(f".{to}")
        errorfile = self.path_to_file.with_suffix(f".{to}.error.txt")
        template = Path(__file__).parent / "templates" / "report_template.tpl"

        def __run():
            cmd = [
                "jupyter",
                "nbconvert",
                str(self.path_to_file),
                "--to",
                to,
                "--no-input",
                "--execute",
                f"--template={template}",
            ]
            with errorfile.open("w") as err:
                print(" ".join(cmd))
                subprocess.check_call(cmd, stderr=err)

        return (
            ppg.FileGeneratingJob(outfile, __run)
            .depends_on(self.dependencies)
            .depends_on(self.write())
            .depends_on(ppg.FileInvariant(template))
        )

