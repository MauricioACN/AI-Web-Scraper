import streamlit as st
from scrape import (
    scrape_website,
    extract_body_content,
    clean_body_content,
    split_dom_content,
    fetch_reviews,
    fetch_highlights,
    fetch_features,
)

# Streamlit UI
st.title("AI Web Scraper")
url = st.text_input("Enter Website URL")

# Step 1: Scrape the Website
if st.button("Scrape Website"):
    if url:
        st.write("Scraping the website...")

        # Scrape the website
        dom_content = scrape_website(url)
        body_content = extract_body_content(dom_content)
        cleaned_content = clean_body_content(body_content)

        # Store the DOM content in Streamlit session state
        st.session_state.dom_content = cleaned_content

        # Display the DOM content in an expandable text box
        with st.expander("View DOM Content"):
            st.text_area("DOM Content", cleaned_content, height=300)


# Step 2: Ask Questions About the DOM Content
if "dom_content" in st.session_state:
    parse_description = st.text_area("Describe what you want to parse")

    if st.button("Parse Content"):
        if parse_description:
            st.write("Parsing the content...")

            # Parse the content with Ollama
            # dom_chunks = split_dom_content(st.session_state.dom_content)
            # parsed_result = parse_with_ollama(dom_chunks, parse_description)
            product_id = "0762121P"  # Producto de prueba

            print("Fetching reviews...")
            reviews = fetch_reviews(product_id)
            print(f"✅ Total reviews fetched: {len(reviews)}")

            print("\nFetching highlights...")
            highlights = fetch_highlights(product_id)
            print(f"✅ Highlights found: {len(highlights.keys())}")

            print("\nFetching features...")
            features = fetch_features(product_id)
            print(f"✅ Features found: {[f['feature'] for f in features]}")

            parsed_result = {
                "reviews": reviews,
                "highlights": highlights,
                "features": features
            }
            st.write(parsed_result)
