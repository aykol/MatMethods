# coding: utf-8

from __future__ import division, print_function, unicode_literals, \
    absolute_import

import os
import shutil

from fireworks import FireTaskBase, explicit_serialize
from pymatgen.io.vasp import Incar, Kpoints, Poscar, Potcar
from matmethods.utils.utils import get_logger

__author__ = 'Anubhav Jain'
__email__ = 'ajain@lbl.gov'

module_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
reference_dir = os.path.join(module_dir, "reference_files")
fake_dirs = {"structure optimization": os.path.join(reference_dir,
                                                    "Si_structure_optimization"),
             "static": os.path.join(reference_dir, "Si_static"),
             "nscf uniform": os.path.join(reference_dir, "Si_nscf_uniform"),
             "nscf line": os.path.join(reference_dir, "Si_nscf_line")}

logger = get_logger(__name__)


@explicit_serialize
class RunVaspFake(FireTaskBase):
    required_params = ["fake_dir"]

    def run_task(self, fw_spec):
        self._verify_inputs()
        self._clear_inputs()
        self._generate_outputs()

    def _verify_inputs(self):
        user_incar = Incar.from_file(os.path.join(os.getcwd(), "INCAR"))
        ref_incar = Incar.from_file(
            os.path.join(self["fake_dir"], "inputs", "INCAR"))

        # perform some BASIC tests

        # check INCAR
        params_to_check = ["ISPIN", "ENCUT", "ISMEAR", "SIGMA", "IBRION",
                           "LORBIT", "NBANDS", "LMAXMIX"]
        defaults = {"ISPIN": 1, "ISMEAR": 1, "SIGMA": 0.2}
        for p in params_to_check:
            if user_incar.get(p, defaults.get(p)) != ref_incar.get(p,
                                                                   defaults.get(
                                                                       p)):
                raise ValueError(
                    "INCAR value of {} is inconsistent!".format(p))

        # check KPOINTS
        user_kpoints = Kpoints.from_file(os.path.join(os.getcwd(), "KPOINTS"))
        ref_kpoints = Kpoints.from_file(
            os.path.join(self["fake_dir"], "inputs", "KPOINTS"))
        if user_kpoints.style != ref_kpoints.style \
                or user_kpoints.num_kpts != ref_kpoints.num_kpts:
            raise ValueError("KPOINT files are inconsistent! "
                             "Paths are:\n{}\n{}".format(
                os.getcwd(), os.path.join(self["fake_dir"], "inputs")))

        # check POSCAR
        user_poscar = Poscar.from_file(os.path.join(os.getcwd(), "POSCAR"))
        ref_poscar = Poscar.from_file(
            os.path.join(self["fake_dir"], "inputs", "POSCAR"))
        if user_poscar.natoms != ref_poscar.natoms or user_poscar.site_symbols != ref_poscar.site_symbols:
            raise ValueError("POSCAR files are inconsistent! "
                             "Paths are:\n{}\n{}".format(
                os.getcwd(), os.path.join(self["fake_dir"], "inputs")))

        # check POTCAR
        user_potcar = Potcar.from_file(os.path.join(os.getcwd(), "POTCAR"))
        ref_potcar = Potcar.from_file(
            os.path.join(self["fake_dir"], "inputs", "POTCAR"))
        if user_potcar.symbols != ref_potcar.symbols:
            raise ValueError("POTCAR files are inconsistent! "
                             "Paths are:\n{}\n{}".format(
                os.getcwd(), os.path.join(self["fake_dir"], "inputs")))
        logger.info("RunVaspFake: verified inputs successfully")

    def _clear_inputs(self):
        for x in ["INCAR", "KPOINTS", "POSCAR", "POTCAR", "CHGCAR", "OUTCAR",
                  "vasprun.xml"]:
            p = os.path.join(os.getcwd(), x)
            if os.path.exists(p):
                os.remove(p)

    def _generate_outputs(self):
        output_dir = os.path.join(self["fake_dir"], "outputs")
        for file_name in os.listdir(output_dir):
            full_file_name = os.path.join(output_dir, file_name)
            if os.path.isfile(full_file_name):
                shutil.copy(full_file_name, os.getcwd())
        logger.info("RunVaspFake: ran fake VASP, generated outputs")
