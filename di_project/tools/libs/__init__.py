from di_project.tools.libs import (
    data_preprocess,
    email_login,
    feature_engineering,
    gpt_v_generator,
    sd_engine,
    terminal,
    web_scraping,
)

_ = (
    data_preprocess,
    feature_engineering,
    sd_engine,
    gpt_v_generator,
    web_scraping,
    email_login,
    terminal,
)  # Avoid pre-commit error
