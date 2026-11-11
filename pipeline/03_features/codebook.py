"""Labeling codebook (NOTES §5). v1 = the hand-label validation round (single topic). v2 = production, after
Sanjay's review of 100 headlines (2026-11-10): topics become yes/no tags (several per headline allowed) and
LGBTQ+ merges with women & gender equality.

Each headline (headline_clean, plus the excerpt where shown) gets three labels, judged only from what the reader
saw on the tile (R8): who it centers by gender, its overall tone, and its perceived topic.
"""

GENDER = {
    "female": "The headline's main person or people are presented as female: she/her, woman, girl, mom, wife, "
              "a recognizably female name, or women as a group.",
    "male": "The main person or people are presented as male: he/his, man, guy, boy, dad, husband, a recognizably "
            "male name, or men as a group.",
    "both": "Female and male people are both central (e.g. 'a husband… his wife', 'a girl said… to this guy').",
    "none": "No gendered person: no people, or only gender-neutral references (people, kids, someone, they, "
            "a comedian, a scientist). Idioms like 'good guys and bad guys' count as none.",
}
SENTIMENT = {
    "positive": "The overall feeling the headline is built to give is good: uplifting, admiring, hopeful, delighted, funny.",
    "neutral": "Informational, curious or flat, with no clear emotional pull; or positive and negative evenly balanced.",
    "negative": "The overall feeling is bad: sad, angry, outraged, fearful, disgusted, alarming.",
}
SENTIMENT_RULE = ("Judge the headline as a whole. When it sets up a bad situation and resolves it ('…but she's not "
                  "havin' it'), label the note it ends on.")
TOPIC = {
    "POL": ("Politics, government & world affairs", "Elections, laws, politicians, war and conflict, surveillance"),
    "RAC": ("Race, ethnicity, religion & immigration", "Racism, racial identity, religious identity, immigrants"),
    "LGB": ("LGBTQ+", "Gay, lesbian, bisexual, transgender people and rights, same-sex marriage"),
    "WOM": ("Women & gender equality", "Sexism, double standards, body image, sexual violence and harassment, women's achievements"),
    "HEA": ("Health & medicine", "Physical, mental and reproductive health, disease, doctors, drugs, vaccines"),
    "ECO": ("Economy, work & inequality", "Wages, jobs, poverty, hunger, housing, corporations, money"),
    "EDU": ("Education", "Schools, teachers, students, learning"),
    "FAM": ("Children, parenting & family", "Kids, parenting advice, family life"),
    "ENV": ("Environment & climate", "Climate change, pollution, oceans, disasters, conservation"),
    "CRI": ("Crime, police & justice", "Police, prisons, courts, guns, the death penalty, crime"),
    "SCI": ("Science & technology", "Science, inventions, coding, space, how things work"),
    "ENT": ("Entertainment, media & pop culture", "Celebrities, comedians, TV, film, music, news media"),
    "HUM": ("Human interest & kindness", "Personal stories, heroes, generosity, overcoming hardship, inspiration"),
    "UNC": ("Unclear from the headline", "A reader couldn't tell what the story is about (curiosity-gap headlines)"),
}
TOPIC_RULE = "Pick the one topic a reader would most likely think the story is about. If two fit, pick the more specific one."


# ---------------------------------------------------------------------------------------------- v2 (production)
# Gender and sentiment are unchanged from v1 (Sanjay: satisfied with both after 100 headlines).
# Topics: one yes/no column per topic (topic_POL ... topic_HUM), so a headline can carry several (R12).
# LGB and WOM merge into GEN (R13). UNC is no longer a choice: a headline with no topic tagged is "unclear".
TOPIC_V2 = {
    "POL": ("Politics, government & world affairs", "Elections, laws, politicians, war and conflict, surveillance"),
    "RAC": ("Race, ethnicity, religion & immigration", "Racism, racial identity, religious identity, immigrants"),
    "GEN": ("Gender equality & LGBTQ+", "Sexism and double standards, women's rights and achievements, body image, sexual "
            "violence and harassment, gay, lesbian, bisexual and transgender people and their rights"),
    "HEA": ("Health & medicine", "Physical, mental and reproductive health, disease, doctors, drugs, vaccines"),
    "ECO": ("Economy, work & inequality", "Wages, jobs, poverty, hunger, housing, corporations, money"),
    "EDU": ("Education", "Schools, teachers, students, learning"),
    "FAM": ("Children, parenting & family", "Kids, parenting advice, family life"),
    "ENV": ("Environment & climate", "Climate change, pollution, oceans, disasters, conservation"),
    "CRI": ("Crime, police & justice", "Police, prisons, courts, guns, the death penalty, crime"),
    "SCI": ("Science & technology", "Science, inventions, coding, space, how things work"),
    "ENT": ("Entertainment, media & pop culture", "Celebrities, comedians, TV, film, music, news media"),
    "HUM": ("Human interest & kindness", "Personal stories, heroes, generosity, overcoming hardship, inspiration"),
}
TOPIC_RULE_V2 = ("Tag every topic a reader would reasonably take from the headline (usually 1 or 2, at most 3). "
                 "Tag none if a reader couldn't tell what the story is about; that headline counts as 'unclear'.")
V1_TO_V2 = {"LGB": "GEN", "WOM": "GEN", "UNC": None}   # how v1 single labels map onto v2 tags (others unchanged)
