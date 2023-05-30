#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""notebook.py: Contains different wrapper for variant caller."""

from pathlib import Path
from typing import List, Union, Literal, Iterable
from pypipegraph2 import Job, MultiFileGeneratingJob, PlotJob
from abc import ABC, abstractmethod
from .htmlmod import GSEAReportPathModifier
import nbformat as nbf
import pypipegraph2 as ppg2
import os
import subprocess

__author__ = "Marco Mernberger"
__copyright__ = "Copyright (c) 2020 Marco Mernberger"
__license__ = "mit"


def flatten(list_of_lists: Iterable) -> Iterable:
    """
    Flattens a nested list
    """
    if not hasattr(list_of_lists, "__iter__"):
        return [list_of_lists]
    flat = []
    list_of_lists = list(list_of_lists)
    while len(list_of_lists) != 0:
        item = list_of_lists.pop(0)
        if hasattr(item, "__iter__"):
            flat.extend(item)
        else:
            flat.append(item)
    return flat


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
            raise ValueError(f"Cell type must be any of [markdown, code], was {celltype}.")
        self.type = celltype
        self.tags = tags
        self.meta = {}
        if len(self.tags) > 0:
            self.meta["tags"] = self.tags
        self.__hash = (self.text + self.type + "".join(self.tags)).__hash__()

    @property
    def hash(self):
        return self.__hash

    def __str__(self):
        return f"Cell(text={self.text}, celltype={self.type}, tags={self.tags})"


class Item(ABC):
    """
    Abstract class for a single item added to the report notebook.

    An Item might be a single plot, an html document, a markdown cell,
    a code cell and anything thast might be added to a report.

    Parameters
    ----------
    section : str
        Section name, used for grouping and header. Items with the same
        section_name will be grouped together.
    section_index : int, optional
        Index of the section, used to order the sections and color the frame,
        by default None. Sections with index None will be added last.
    """

    def __init__(
        self,
        section: str,
        tags: List[str] = None,
        color: bool = True,
        dependencies: List[Job] = [],
    ):
        """constructor"""
        self.section = section
        self._tags = tags
        if tags is None:
            self._tags = []
        self._dependencies = dependencies
        self.color = color

    @property
    def dependencies(self) -> List[Job]:
        return self._dependencies

    @property
    def tags(self):
        return self._tags

    def add_tag(self, tag: str):
        self._tags.append(tag)

    @abstractmethod
    def cells(self, result_dir: str, tags: List[str] = []) -> List[Cell]:
        """
        Returns a list of cells to be added to the notebook from this item.

        A single item can add multiple cells which are added in the order
        they are returned.

        Returns
        -------
        List[Cell]
            List of cells to be added.
        """
        pass


class PlotItem(Item):
    def __init__(
        self,
        section: str,
        job: PlotJob,
        text: str = None,
        tags: List[str] = None,
        color: bool = True,
    ):
        """
        Returns a callable that creates a list of cells, an optional markdown
        cell with a figure text and a cell loading the created figure.

        Overrides the abstract super class method.

        Parameters
        ----------
        job : PlotJob
            PlotJob that created the file
        text : str, optional
            Text as header for the figure, by default None.
        tags : List[str], optional
            List of optional tags for the notebook cell, by default None.

        Returns
        -------
        List[Cell]
            List of cells to add.
        """
        if not hasattr(job, "__iter__"):
            jobs = [job]
        else:
            jobs = job
        super().__init__(section, tags, color, dependencies=job)
        self.text = text
        if text is None:
            self.text = f"Result from : {self.job.job_id}"
 
    def cells(self, result_dir: str, tags: List[str] = []) -> List[Cell]:
        cells = []
        cells.append(Cell(f"{self.text}", "markdown", self.tags))
        jobs = flatten(self.job)
        filenames = []
        for job in jobs:
            print(job, type(job))
            if isinstance(job, MultiFileGeneratingJob):
                filenames.extend(job.files)
        filenames = [
            os.path.relpath(Path(filename).resolve(), result_dir)
            for filename in filenames
            if filename.name.endswith(".png")
        ]
        print(filenames)
        code = f"""\
for filename in {filenames}:
    display(Image(filename, embed=True, retina=True))
"""
        cells.append(Cell(code, "code", self.tags))
        return cells


class MarkdownItem(Item):
    def __init__(
        self,
        section: str,
        text: str,
        tags: List[str] = None,
        format: int = 0,
        color: bool = True,
    ):
        super().__init__(section, tags, color)
        if format == 1:
            self.text = f"### **{self.text}**:"
        else:
            self.text = text

    def cells(self, result_dir: str, tags: List[str] = []) -> List[Cell]:
        cell = Cell(self.text, "markdown", self.tags)
        return [cell]


class CodeItem(Item):
    def __init__(self, section: str, text: str, tags: List[str] = None, color: bool = True):
        super().__init__(section, tags, color)
        self.text = text

    def cells(self, result_dir: str, tags: List[str] = []) -> List[Cell]:
        cell = Cell(self.text, "code", tags + self.tags)
        return [cell]


class HTMLItem(Item):
    def __init__(
        self,
        section: str,
        filename: Path,
        job: Job,
        tags: List[str] = None,
        color: bool = True,
    ):
        super().__init__(section, tags, color, dependencies=[job])
        self.text = f"#### HTML from : {filename}"
        self.filename = filename
        self.dependencies.extend(job)

    def cells(self, result_dir: str, tags: List[str] = []) -> List[Cell]:
        cells = []
        cell = Cell(self.text, "markdown", self.tags)
        cells.append(cell)
        rel_filename = os.path.relpath(Path(self.filename).resolve(), result_dir)
        code = f'HTML(filename="{rel_filename}")'
        cell = Cell(code, "code", self.tags)
        cells.append(cell)
        return cells


class GSEAHTMLItem(HTMLItem):
    def __init__(
        self,
        section: str,
        filename: Path,
        job: Job,
        tags: List[str] = None,
        color: bool = True,
    ):
        mod_job = GSEAReportPathModifier().job(filename, [job])
        filename = self.get_filename(mod_job)
        super().__init__(section, filename, mod_job, tags, color)
        
    def get_filename(self, mod_job: Job) -> Path:
        return Path(mod_job.job_id).resolve()

# deal woith hash and order
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
    dependencies : List[Job], optional
        Job dependencies.
    """

    def __init__(self, name: str, path_to_directory: Path = None, dependencies: List[Job] = []):
        self.name = name
        self.project_name = Path.cwd().name
        if "ANYSNAKE_PROJECT_PATH" in os.environ:
            self.project_name = Path(os.environ["ANYSNAKE_PROJECT_PATH"]).name
        elif "ANYSNAKE2_SOURCE" in os.environ:
            self.project_name = Path(os.environ["ANYSNAKE2_SOURCE"]).name
        self.result_dir = path_to_directory
        if self.result_dir is None:
            self.result_dir = Path("out") / "notebooks"
        self.result_dir.mkdir(exist_ok=True, parents=True)
        self.path_to_file = self.result_dir / f"{self.name}_{self.project_name}.ipynb"
        self.sections: Dict[str, List] = {}
        self.section_order: List[str] = []
        self.nb = nbf.v4.new_notebook()
        self.invariant: List[str] = []
        self._dependencies: List[Job] = []
        self._dependencies.extend(dependencies)
        self._dependencies.extend(
            [
                ppg2.FunctionInvariant(str(self.path_to_file) + "plot_cells", PlotItem.cells),
                ppg2.FunctionInvariant(str(self.path_to_file) + "text_cell", MarkdownItem.cells),
                ppg2.FunctionInvariant(str(self.path_to_file) + "_html_cells", HTMLItem.cells),
                ppg2.FunctionInvariant(str(self.path_to_file) + "_commitfunc", self.__commit),
                ppg2.FunctionInvariant(str(self.path_to_file) + "_register", self.register_item),
                ppg2.FunctionInvariant(str(self.path_to_file) + "_initfirst", self.init_first_cell),
                ppg2.FunctionInvariant(
                    str(self.path_to_file) + "__make_ordered_list",
                    self.__make_ordered_list,
                ),
            ]
        )
        self.first_cells = self.init_first_cell()

    colors = {
        0: "green",
        1: "blue",
        2: "orange",
        3: "red",
        4: "yellow",
        5: "cyan",
        6: "purple",
    }

    def get_color_tag(self, section):
        section_index = self.section_order.index(section)
        if section_index >= len(self.colors):
            section_index = section_index % len(self.colors)
        return self.colors[section_index]

    @property
    def dependencies(self):
        return self._dependencies

    def register_item(self, item: Item):
        # add an item to the dictionary of sections
        if item.section not in self.sections:
            self.section_order.append(item.section)
            self.sections[item.section] = []
        self.sections[item.section].append(item)
        self.add_dependencies(item.dependencies)

    def add_dependencies(self, jobs: Union[Job, List[Job]]):
        if isinstance(jobs, list):
            self._dependencies.extend(jobs)
        elif isinstance(jobs, Job):
            self._dependencies.append(jobs)
        else:
            raise ValueError("Given job is not a Job instance or list.")

    # def __register_cell(
    #     self,
    #     content: str,
    #     celltype: str,
    #     tags: List[str] = None,
    #     section_index: int = None,
    # ):
    #     if tags is None:
    #         tags = []
    #     if section_index is not None:
    #         tags.append(self.get_color_tag(section_index))
    #     cell = Cell(content, celltype, tags)
    #     self.ordered_cell_list.append(cell)
    #     self.invariant.append(cell.hash)s

    def init_first_cell(self):
        cells = []
        text = """\
from IPython.display import Image
from IPython.display import HTML
"""
        cell = Cell(text, celltype="code")
        cells.append(cell)
        text = f"""\
## Analysis report for
## {self.project_name}.
        """
        cell = Cell(text, celltype="markdown")
        cells.append(cell)
        text = """\
%%html
<style>
    table {
        display: inline-block
    }
</style>
"""
        cell = Cell(text, "code")
        cells.append(cell)
        return cells

    #     def register_plot(
    #         self,
    #         job: PlotJob,
    #         text: str = None,
    #         tags: List[str] = None,
    #         section_index: int = None,
    #     ):
    #         if text is None:
    #             text = f"Result from : {job.job_id}"
    #         self.__register_cell(f"{text}:", "markdown", tags, section_index)
    #         filenames = [
    #             os.path.relpath(Path(f).resolve(), self.result_dir)
    #             for f in job.filenames
    #             if f.endswith(".png")
    #         ]
    #         code = f"""\
    # for filename in {filenames}:
    #     display(Image(filename, embed=True, retina=True))
    # """
    #         self.__register_cell(code, "code", tags, section_index)
    #         self.dependencies.extend(job)

    # def register_text(
    #     self, text: str, tags: List[str] = None, section_index: int = None,
    # ):
    #     self.__register_cell(f"### **{text}**:", "markdown", tags, section_index)

    # def register_code(
    #     self, text: str, tags: List[str] = None, section_index: int = None,
    # ):
    #     self.__register_cell(text, "code", tags, section_index)

    # def register_markdown(
    #     self, text: str, tags: List[str] = None, section_index: int = None,
    # ):
    #     self.__register_cell(text, "markdown", tags, section_index)

    # def register_html(
    #     self,
    #     filename: Path,
    #     job,
    #     text: str = None,
    #     tags: List[str] = None,
    #     section_index: int = None,
    # ):
    #     if text is None:
    #         text = f"HTML from : {filename}"
    #     self.__register_cell(f"#### {text}:", "markdown", tags, section_index)
    #     rel_filename = os.path.relpath(Path(filename).resolve(), self.result_dir)
    #     code = f'HTML(filename="{rel_filename}")'
    #     self.__register_cell(code, "code", tags, section_index)
    #     self.dependencies.extend(job)

    # def register_file(
    #     self,
    #     job: Union[FileGeneratingJob, MultiFileGeneratingJob],
    #     text: str,
    #     tags: List[str] = None,
    #     section_index: int = None,
    # ):
    #     if isinstance(job, FileGeneratingJob):
    #         if text is None:
    #             text = f"File {job.job_id}"
    #         self.__register_cell(f"### **{text}**:", "markdown", tags, section_index)

    # def register_item(item: Item):
    #     #add an item to the dictionary of sections
    #     if item.section not in self.sections:
    #         self.section_order.append(item.section)
    #         self.sections[item.section] = []
    #     self.sections[item.section].append(item)

    def __make_ordered_list(self):
        ordered_list = []
        ordered_list.extend(self.first_cells)
        for section in self.section_order:
            for item in self.sections[section]:
                if item.color:
                    print("color", self.get_color_tag(section))
                    item.add_tag(self.get_color_tag(section))
                cells = item.cells(self.result_dir)
                ordered_list.extend(cells)
        return ordered_list

    def __commit(self):
        self.nb["cells"] = []
        ordered_cell_list = self.__make_ordered_list()
        invariants = []
        for cell in ordered_cell_list:
            if cell.type == "markdown":
                self.nb["cells"].append(nbf.v4.new_markdown_cell(cell.text, metadata=cell.meta))
            else:
                self.nb["cells"].append(nbf.v4.new_code_cell(cell.text, metadata=cell.meta))
            invariants.append(cell.hash)
        self.dependencies.append(ppg2.ParameterInvariant(self.name + "__hash", invariants))

    def write(self):
        path_to_file = self.path_to_file

        def do_write(path_to_file):
            self.__commit()
            with path_to_file.open("w") as outp:
                nbf.write(self.nb, outp)

        return ppg2.FileGeneratingJob(path_to_file, do_write).depends_on(self.dependencies)

    def convert(self, to: str = "html"):
        outfile = self.path_to_file.with_suffix(f".{to}")
        errorfile = self.path_to_file.with_suffix(f".{to}.error.txt")
        template = Path(__file__).parent / "templates" / "report_template.tpl"
        path_to_file = self.path_to_file

        def __run(*_):
            cmd = [
                "jupyter",
                "nbconvert",
                str(path_to_file),
                "--to",
                to,
                "--no-input",
                "--execute",
                # f"--template={template}",  # this is currently bugged in nbconvert
            ]
            with errorfile.open("w") as err:
                print(" ".join(cmd))
                subprocess.check_call(cmd, stderr=err)

        return (
            ppg2.FileGeneratingJob(outfile, __run)
            .depends_on(self.dependencies)
            .depends_on(self.write())
            .depends_on(ppg2.FileInvariant(template))
        )
