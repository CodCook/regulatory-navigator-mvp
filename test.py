from app import mock_ai_extraction, run_gap_analysis, generate_recommendations
data = mock_ai_extraction("irrelevant")
print('extracted:', data)
gaps = run_gap_analysis(data)
print('gaps:', gaps)
print('recs:', generate_recommendations(gaps))