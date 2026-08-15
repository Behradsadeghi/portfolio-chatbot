"""
extract_chunks.py

Gam-e 1-e data layer: az index.html-e site, chunk-haye tamiz va
manadar biroon mikeshim baraye estefade dar RAG pipeline.

Chera in tor: site-e ma az ghabl be bakhsh-haye tabi'i taghsim shode
(About, Work Experience, Projects, Skills) - pas har bakhsh-o be onvan
ye chunk mantazi migirim, na be soorat-e keyfi/token-based split.
"""

import json
from bs4 import BeautifulSoup

from .config import SITE_PATH, CHUNKS_PATH as OUTPUT_PATH


def clean_text(el) -> str:
    """Get text from a tag, collapse whitespace, drop empty lines."""
    text = el.get_text(separator=" ", strip=True)
    return " ".join(text.split())


def extract_about(soup) -> dict:
    article = soup.find("article", class_="about")
    about_text = clean_text(article.find("section", class_="about-text"))
    interests = [
        clean_text(li) for li in article.select(".service-list .service-item")
    ]
    return {
        "section": "about",
        "title": "About Behrad Sadeghi",
        "text": f"{about_text} Interests: {', '.join(interests)}.",
    }


def extract_education(soup) -> list[dict]:
    chunks = []
    article = soup.find("article", class_="resume")
    edu_section = article.find("h3", string="Education").find_parent("section")
    for item in edu_section.select(".timeline-item"):
        title = clean_text(item.find("h4"))
        span = clean_text(item.find("span"))
        text = clean_text(item.find("p"))
        chunks.append(
            {
                "section": "education",
                "title": title,
                "text": f"{title} ({span}). {text}",
            }
        )
    return chunks


def extract_work_experience(soup) -> list[dict]:
    """
    CHERA HAR SHOGHL YE CHUNK-E, NA HAR BULLET
    ------------------------------------------
    Split kardan-e har bullet ro emtehan kardim (faraziye: chunk-e
    kutah-tar = vector-e motemarkez-tar = rank-e behtar).

    Natije-ye eval: recall@3 az 95.8% oft kard be 87.5%, va recall@8
    az 100% be 95.8%. Badtar shod.

    CHERA: har bullet onvan-e shoghl ro jelosh dasht (~15 kalame-ye
    yeksan) ta context hefz beshe. Hamun onvan bae'z shod chunk-haye
    khahar-baradar vector-e kheili nazdik begiran - ba ham khoshe
    mishodan va do-se ta ja-ye top-k ro por mikardan, va chunk-haye
    mote'aded ro birun mizadan. Tuye eval didim do chunk-e yek shoghl
    do ta ja-ye top-3 ro gereftan.

    DARS: tamarkoz be tanhaii kafi nist - TANAVVO' ham lazem-e.
    (Age ye rooz vaghean chunk-e split lazem shod, rah-e hal
    MMR / diversity-aware retrieval-e: mahdud kardan-e teh'dad-e
    chunk az yek manba' tuye natayej.)
    """
    chunks = []
    article = soup.find("article", class_="resume")
    work_section = article.find("h3", string="Work Experience").find_parent("section")
    for item in work_section.select(".timeline-item"):
        title = clean_text(item.find("h4"))
        span = clean_text(item.find("span"))
        text = clean_text(item.find("p"))
        chunks.append(
            {
                "section": "work_experience",
                "title": title,
                "text": f"{title} ({span}). {text}",
            }
        )
    return chunks


def extract_projects(soup) -> list[dict]:
    chunks = []
    article = soup.find("article", class_="portfolio")
    for item in article.select(".timeline-item"):
        title = clean_text(item.find("h4"))
        link_tag = item.find("a")
        url = link_tag["href"] if link_tag else None
        text = clean_text(item.find("p"))
        chunks.append(
            {
                "section": "project",
                "title": title,
                "url": url,
                "text": f"{title}: {text}",
            }
        )
    return chunks


def extract_skills(soup) -> list[dict]:
    chunks = []
    article = soup.find("article", class_="skills")
    for sec in article.select(".skills-sec"):
        category = clean_text(sec.find("h3"))
        items = [clean_text(p) for p in sec.select(".skills-details p")]
        chunks.append(
            {
                "section": "skills",
                "title": category,
                "text": f"{category}: {', '.join(items)}.",
            }
        )
    return chunks


def extract_contact(soup) -> dict:
    """
    CHERA IN JODA AZ BAGHIYE-ST
    ---------------------------
    Baghiye-ye extractor-ha dakhel-e <article> migardan (About, Resume,
    Projects, Skills). Vali contact info tuye <aside class="sidebar">
    hast - birun az un article-ha, chon tuye HAR safhe neshun dade mishe.

    Dars: sakhtar-i ke chashm-e to mibine ba sakhtar-i ke code mibine
    yeki nist. Hamishe baad az extract, khoruji ro check kon ke chi ja
    mande.

    TASMIM-E AGAHANE: tarikh-e tavallod ro AZ GHASD nemiarim tu index.
    Baraye recruiter bi-fayede-st, va nemikhaym chatbot tabdil beshe be
    ye API-ye rahat baraye keshidan-e PII.
    """
    aside = soup.find("aside", class_="sidebar")

    fields = {}
    for item in aside.select(".contact-item"):
        label_tag = item.find("p", class_="contact-title")
        value_tag = item.find(["a", "address", "time"])
        if not label_tag or not value_tag:
            continue
        label = clean_text(label_tag)
        if label.lower() == "birthday":  # amdan skip mishe
            continue
        fields[label] = clean_text(value_tag)

    socials = {}
    for link in aside.select(".social-item a"):
        icon = link.find("ion-icon")
        if icon and icon.get("name"):
            platform = icon["name"].replace("logo-", "").capitalize()
            socials[platform] = link["href"]

    parts = [f"{k}: {v}" for k, v in fields.items()]
    parts += [f"{k}: {v}" for k, v in socials.items()]

    return {
        "section": "contact",
        "title": "Contact information",
        "text": (
            "You can reach Behrad Sadeghi through the following. "
            + " ".join(parts)
        ),
    }


def main():
    html = SITE_PATH.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    chunks = []
    chunks.append(extract_about(soup))
    chunks.append(extract_contact(soup))
    chunks.extend(extract_education(soup))
    chunks.extend(extract_work_experience(soup))
    chunks.extend(extract_projects(soup))
    chunks.extend(extract_skills(soup))

    OUTPUT_PATH.write_text(
        json.dumps(chunks, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Extracted {len(chunks)} chunks -> {OUTPUT_PATH}")
    print()
    print("Sample chunks:")
    for c in chunks[:3]:
        print(f"  [{c['section']}] {c['title']}")
        print(f"    {c['text'][:140]}...")
        print()


if __name__ == "__main__":
    main()
