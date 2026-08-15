from src.connectors.csv_connector import CSVConnector

def test_csv_connector():

    connector = CSVConnector(
        "data/raw/financial.csv"
    )

    records = connector.fetch()

    assert len(records) == 2
    assert records[0].source == "csv"