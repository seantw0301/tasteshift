# Qloo tag review

Status: **confirmed** by the owner. Stored as `confirmed` in `qloo_tag_candidates.json` (`reviewed: true`); the gateway uses only these URNs.

| Concept | Proposed URN | Why | Alternatives |
|---|---|---|---|
| anime | `urn:tag:genre:qloo:anime` | type matches the demo concept | `urn:tag:subgenre:qloo:anime`, `urn:tag:interests:qloo:anime` |
| collectibles | `urn:tag:interests:qloo:collectibles` | type matches the demo concept | `urn:tag:product_service:qloo:collectibles`, `urn:tag:hobby:qloo:collector` |
| cosplay | `urn:tag:interests:qloo:cosplay` | type matches the demo concept | `urn:tag:keyword:media:cosplay`, `urn:tag:keyword:media:cosplayer` |
| crafts | `urn:tag:genre:qloo:crafts` | type matches the demo concept | `urn:tag:decor:qloo:arts_and_crafts`, `urn:tag:decor:qloo:crafty` |
| eco | `urn:tag:ambience:qloo:ecological` | type matches the demo concept | `urn:tag:adjective:qloo:eco_friendly`, `urn:tag:subgenre:qloo:ecology` |
| family | `urn:tag:genre:qloo:family` | type matches the demo concept | `urn:tag:lifestyle:qloo:family`, `urn:tag:keyword:qloo:family` |
| gaming | `urn:tag:genre:qloo:gaming` | type matches the demo concept | `urn:tag:hobby:qloo:gaming`, `urn:tag:lifestyle:qloo:gaming` |
| gifting | `urn:tag:lifestyle:qloo:gift_giving` | type matches the demo concept | `urn:tag:lifestyle:qloo:gifting`, `urn:tag:good_for:qloo:gifting` |
| j-pop | `urn:tag:genre:music:j_pop` | type matches the demo concept | `urn:tag:genre:qloo:j_pop`, `urn:tag:genre:music:jpop` |
| jpop | `urn:tag:genre:music:jpop` | type matches the demo concept | `urn:tag:genre:music:j_pop`, `urn:tag:genre:qloo:j_pop` |
| kawaii | `urn:tag:decor:qloo:kawaii` | type matches the demo concept | `urn:tag:keyword:qloo:kawaii`, `urn:tag:interests:qloo:kawaii_culture` |
| kids | `urn:tag:subgenre:qloo:kids` | type matches the demo concept | `urn:tag:keyword:qloo:kids`, `urn:tag:genre:media:kids` |
| local culture | `urn:tag:cultural_relevance:qloo:local_culture` | type matches the demo concept | `urn:tag:culture:qloo:local_markets`, `urn:tag:culture:qloo:local_festivals` |
| lunar new year | `urn:tag:culture:qloo:chinese_new_year` | type matches the demo concept | `urn:tag:culture:qloo:lunar_new_year_celebrations`, `urn:tag:culture:qloo:chinese_new_year_celebrations` |
| music live | `urn:tag:music:qloo:live` | type matches the demo concept | `urn:tag:genre:music:live`, `urn:tag:music_characteristic:qloo:live` |
| outdoor | `urn:tag:lifestyle:qloo:outdoor` | type matches the demo concept | `urn:tag:lifestyle:qloo:outdoor_living`, `urn:tag:lifestyle:qloo:outdoors` |
| picture books | `urn:tag:genre:qloo:picture_book` | type matches the demo concept | `urn:tag:genre:media:picture_books`, `urn:tag:subgenre:qloo:picture_book` |
| plush | `urn:tag:decor:qloo:plush` | type matches the demo concept | `urn:tag:ambience:qloo:plush`, `urn:tag:product_service:qloo:plush_toys` |
| stationery | `urn:tag:product_category:qloo:stationery` | type matches the demo concept | `urn:tag:amenity:qloo:stationery`, `urn:tag:product_service:qloo:stationery` |
| streetwear | `urn:tag:personal_style:qloo:streetwear` | type matches the demo concept | `urn:tag:adjective:qloo:streetwear`, `urn:tag:lifestyle:qloo:streetwear_fashion` |
| traditional market | `urn:tag:setting:qloo:traditional_market` | type matches the demo concept | `urn:tag:category:place:traditional_market`, `urn:tag:genre:place:traditional_market` |

## Concepts without candidates

SKU concept tags used by the merchant but never resolved (no URN, so Qloo cannot use them yet):

cheese, classic_snack, festive, grilled, matcha, refreshing, spicy, sweet, tea, traditional, tropical_fruit

Next: run `scripts/qloo_resolve_tags.sh` with these names added to the seed list, then review again.

## Added concepts (confirmed)

SKU concepts with no URN before. Confirmed by the owner and stored in `confirmed`.

| Concept | Proposed URN | Alternatives |
|---|---|---|
| cheese | `urn:tag:cuisine:qloo:cheese` | `urn:tag:cuisine:qloo:cheeses`, `urn:tag:popular_food_item:qloo:cheese` |
| classic snack | `urn:tag:interests:qloo:classic_snacks` | `urn:tag:decor:qloo:classic_snack_bar`, `urn:tag:product_service:qloo:traditional_snacks` |
| festive | `urn:tag:keyword:qloo:festive` | `urn:tag:plot:qloo:festive`, `urn:tag:lifestyle:qloo:festive_celebrations` |
| grilled | `urn:tag:cuisine:qloo:grilled` | `urn:tag:cuisine:qloo:grilled_specialties`, `urn:tag:cuisine:qloo:grilled_food` |
| matcha | `urn:tag:popular_food_item:qloo:matcha` | `urn:tag:cuisine:qloo:matcha`, `urn:tag:cuisine:qloo:matcha_specialties` |
| refreshing | `urn:tag:flavor_profile:qloo:refreshing` | `urn:tag:activity_type:qloo:refreshing`, `urn:tag:ambience:qloo:refreshing` |
| spicy | `urn:tag:flavor_profile:qloo:spicy` | `urn:tag:cuisine:qloo:spicy`, `urn:tag:amenity:qloo:spicy_condiments` |
| sweet | `urn:tag:flavor_profile:qloo:sweet` | `urn:tag:style:qloo:sweet`, `urn:tag:character:qloo:sweet` |
| tea | `urn:tag:popular_food_item:qloo:tea` | `urn:tag:cuisine:qloo:tea`, `urn:tag:product_category:qloo:tea` |
| traditional | `urn:tag:characteristic:qloo:traditional` | `urn:tag:adjective:qloo:traditional`, `urn:tag:style:qloo:traditional` |
| tropical fruit | `urn:tag:popular_food_item:qloo:tropical_fruit` | `urn:tag:interests:qloo:tropical_fruit`, `urn:tag:interests:qloo:tropical_fruits` |

Note: SKU `concept_tags` use underscores (e.g. `tropical_fruit`); the confirmed keys use spaces. Normalize before lookup.
