# Dataset Approval Submission - IS 366 Project 1
**Team:** Basel Alrabiah, Ahmad Alkhalifa, Abdullah Alnajashi

1. **Dataset name and source URL:** No. 18 Google Trends - Retail Product Search Interest. https://trends.google.com/trends/explore
2. **Description and business context:** Monthly search-interest index (0-100) in Saudi Arabia for five retail products, used as a public proxy for consumer demand. Context: a multi-category Saudi retailer planning stock and promotions. Limitation acknowledged: search interest is not actual sales and the index is normalised.
3. **Records and variables:** 274 monthly records (Jan 2004 - Oct 2026; 142 months used from Jan 2015). Variables: Time; iPhone, perfume, deep fryer, bag, firewood (indices 0-100, common scale).
4. **Business problem and forecasting objective:** Identify top products, trends and seasonal peaks, and forecast product-level monthly demand interest for Nov 2026 - Oct 2027 using a chronological train/test split, compared with a seasonal-naive baseline (MAE, RMSE, MAPE).
