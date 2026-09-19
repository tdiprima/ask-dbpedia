"""Pre-defined pathology-related SPARQL queries for DBPedia."""

COMMON_DISEASES = """
SELECT DISTINCT ?disease ?name WHERE {
    ?disease a dbo:Disease .
    ?disease rdfs:label ?name .
    FILTER (lang(?name) = "en")
} LIMIT 10
"""

CANCERS_WITH_ICD10 = """
SELECT DISTINCT ?name ?icd10 WHERE {
    ?disease a dbo:Disease .
    ?disease rdfs:label ?name .
    ?disease dbo:icd10 ?icd10 .
    FILTER (lang(?name) = "en")
    FILTER (regex(?name, "cancer|carcinoma|tumor", "i"))
} LIMIT 10
"""

LIVER_DISEASES = """
SELECT DISTINCT ?name WHERE {
    ?disease a dbo:Disease .
    ?disease rdfs:label ?name .
    FILTER (lang(?name) = "en")
    FILTER (regex(?name, "liver|hepat", "i"))
} LIMIT 10
"""

PATHOLOGY_SCIENTISTS = """
SELECT DISTINCT ?name WHERE {
    ?person dbo:academicDiscipline dbr:Pathology .
    ?person rdfs:label ?name .
    FILTER (lang(?name) = "en")
} LIMIT 10
"""

DISEASES_BY_MEDICAL_SPECIALTY = """
SELECT DISTINCT ?name ?specialty WHERE {
    ?disease a dbo:Disease .
    ?disease rdfs:label ?name .
    ?disease dbo:medicalSpecialty ?specialty .
    FILTER (lang(?name) = "en")
} LIMIT 10
"""

PATHOLOGY_QUERIES = {
    "Common diseases": COMMON_DISEASES,
    "Cancers and ICD-10 codes": CANCERS_WITH_ICD10,
    "Liver diseases": LIVER_DISEASES,
    "Pathology scientists": PATHOLOGY_SCIENTISTS,
    "Diseases by medical specialty": DISEASES_BY_MEDICAL_SPECIALTY,
}
