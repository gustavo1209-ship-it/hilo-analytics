import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

REQUEST_DELAY = float(os.getenv("REQUEST_DELAY_SECONDS", "2.5"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "20"))
USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
)

IG_USERNAME = os.getenv("IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD")

# Concorrentes mapeados no Supabase — slug → instagram handle
COMPETITOR_IG_HANDLES: dict[str, str] = {
    "shop2gether":          "shop2gether",
    "oqvestir":             "oqvestir",
    "mamo":                 "mamoboutique",
    "femme-store":          "femmestoremultimarcas",
    "sl-store":             "slstorenet",
    "gerbella":             "lojagerbella",
    "loja-alegreto":        "lojaalegreto",
    "apice-multimarcas":    "apicemultimarcas",
    "olivia-multimarcas":   "oliviamultimarcas",
    "sedanaya":             "sedanaya",
}

# Targets de e-commerce via API VTEX (sites oficiais das marcas)
# Cada entrada representa uma marca com API VTEX nativa — sem bloqueio de bot.
VTEX_TARGETS: list[dict] = [
    {
        "brand_slug":  "nv",
        "brand_name":  "NV",
        "vtex_url":    "https://www.bynv.com.br",
        "categories":  [
            ("Calcas",   "/Roupas/"),
            ("Vestidos", "/Roupas/"),
            ("Blusas",   "/Roupas/"),
            ("Blazers",  "/Roupas/"),
        ],
        "page_size": 50,
    },
    {
        "brand_slug":  "john-john",
        "brand_name":  "John John",
        "vtex_url":    "https://www.johnjohndenim.com.br",
        "categories":  [
            ("Feminino", "/Feminino/"),
            ("Masculino","/Masculino/"),
        ],
        "page_size": 50,
    },
    {
        "brand_slug":  "calvin-klein",
        "brand_name":  "Calvin Klein",
        "vtex_url":    "https://www.calvinklein.com.br",
        "categories":  [
            ("Feminino", "/Feminino/"),
            ("Underwear","/Underwear/"),
        ],
        "page_size": 50,
    },
]
