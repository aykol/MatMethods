from tqdm import tqdm

from matgendb.util import get_database
from monty.json import jsanitize
from pymatgen import Structure
from pymatgen.analysis.structure_matcher import StructureMatcher, \
    ElementComparator
from pymatgen.electronic_structure.boltztrap import BoltztrapAnalyzer

__author__ = 'Anubhav Jain <ajain@lbl.gov>'


class BoltztrapMaterialsBuilder:
    def __init__(self, materials_write, boltztrap_read):
        """
        Update materials collection based on boltztrap collection
        Args:
            materials_write: mongodb collection for materials (write access needed)
            boltztrap_read: mongodb collection for boltztrap (suggest read-only for safety)
        """
        self._materials = materials_write
        self._boltztrap = boltztrap_read

    def run(self):
        print("BoltztrapMaterialsBuilder starting...")
        print("Initializing list of all new boltztrap ids to process ...")
        previous_oids = []
        for m in self._materials.find({}, {"_boltztrapbuilder.all_object_ids": 1}):
            if '_boltztrapbuilder' in m:
                previous_oids.extend(m["_boltztrapbuilder"]["all_object_ids"])

        if not previous_oids:
            self._build_indexes()

        all_btrap_ids = [i["_id"] for i in self._boltztrap.find({}, {"_id": 1})]
        btrap_ids = [o_id for o_id in all_btrap_ids if o_id not in previous_oids]

        print("There are {} new boltztrap ids to process.".format(len(btrap_ids)))

        pbar = tqdm(btrap_ids)
        for o_id in pbar:
            pbar.set_description("Processing object_id: {}".format(o_id))
            try:
                doc = self._boltztrap.find_one({"_id": o_id})
                m_id = self._match_material(doc)
                if not m_id:
                    raise ValueError("Cannot find matching material for object_id: {}".format(o_id))
                print(m_id)
                self._update_material(m_id, doc)
            except:
                import traceback
                print("<---")
                print("There was an error processing task_id: {}".format(o_id))
                traceback.print_exc()
                print("--->")

        print("BoltztrapMaterialsBuilder finished processing.")

    def reset(self):
        self._materials.update_many({}, {"$unset": {"_boltztrapbuilder": 1,
                                                    "transport": 1}})
        self._build_indexes()

    def _match_material(self, doc):
        """
        Returns the material_id that has the same structure as this doc as
         determined by the structure matcher. Returns None if no match.

        Args:
            doc: a JSON-like document

        Returns:
            (int) matching material_id or None
        """
        formula = doc["formula_reduced_abc"]
        sgnum = doc["spacegroup"]["number"]

        for m in self._materials.find({"formula_reduced_abc": formula, "sg_number": sgnum},
                                      {"structure": 1, "material_id": 1}):

            m_struct = Structure.from_dict(m["structure"])
            t_struct = Structure.from_dict(doc["structure"])

            sm = StructureMatcher(ltol=0.2, stol=0.3, angle_tol=5,
                                  primitive_cell=True, scale=True,
                                  attempt_supercell=False, allow_subset=False,
                                  comparator=ElementComparator())

            if sm.fit(m_struct, t_struct):
                return m["material_id"]

        return None

    def _update_material(self, m_id, doc):
        """
        Update a material document based on a new task

        Args:
            m_id: (int) material_id for material document to update
            doc: a JSON-like Boltztrap document
        """
        bta = BoltztrapAnalyzer.from_dict(doc)
        d = {}
        d["zt"] = bta.get_extreme("zt")
        d["pf"] = bta.get_extreme("power factor")
        d["seebeck"] = bta.get_extreme("seebeck")
        d["conductivity"] = bta.get_extreme("conductivity")
        d["kappa_max"] = bta.get_extreme("kappa")
        d["kappa_min"] = bta.get_extreme("kappa", maximize=False)

        self._materials.update_one({"material_id": m_id}, {"$set": {"transport": d}})
        self._materials.update_one({"material_id": m_id}, {"$push": {"_boltztrapbuilder.all_object_ids": doc["_id"]}})
        self._materials.update_one({"material_id": m_id}, {"$set": {"_boltztrapbuilder.blessed_object_id": doc["_id"]}})

    def _build_indexes(self):
        """
        Create indexes for faster searching
        """
        for x in ["zt", "pf", "seebeck", "conductivity", "kappa_max",
                  "kappa_min"]:
            self._materials.create_index("transport.{}.best.value".format(x))

    @staticmethod
    def from_db_file(db_file, m="materials", b="boltztrap", **kwargs):
        """
        Get a BoltztrapMaterialsBuilder using only a db file
        Args:
            db_file: (str) path to db file
            m: (str) name of "materials" collection
            b: (str) name of "boltztrap" collection
            **kwargs: other params to put into BoltztrapMaterialsBuilder
        """
        db_write = get_database(db_file, admin=True)
        try:
            db_read = get_database(db_file, admin=False)
            db_read.collection_names()  # throw error if auth failed
        except:
            print("Warning: could not get read-only database")
            db_read = get_database(db_file, admin=True)

        return BoltztrapMaterialsBuilder(db_write[m], db_read[b], **kwargs)