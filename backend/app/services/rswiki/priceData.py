import requests

from app.models.priceDataModel import PriceDataModel
BASE_DATA_URL = "https://chisel.weirdgloop.org/gazproj/gazbot/os_dump.json"

"""
EXAMPLE DATA STRUCTURE FROM RSWIKI API:

"10344": {
    "examine": "Fabulously ancient mage protection enchanted in the 3rd Age.",
    "id": 10344,
    "members": true,
    "lowalch": 20200,
    "limit": 8,
    "value": 50500,
    "highalch": 30300,
    "icon": "3rd Age amulet.png",
    "name": "3rd Age amulet",
    "price": 43791831,
    "last": 43791831,
    "volume": 16
  }


  {
    id: 10344,
    members: true,
    lowalch: 20200,
    limit: 8,
    value: 50500,
    highalch: 30300,
    icon: "3rd Age amulet.png",
    name: "3rd Age amulet",
    price: 43791831,
    last: 43791831,
    volume: 16
  }



"""

class RSWikiPriceData:
    def __init__(self):
        self.base_url = BASE_DATA_URL
        self.priceData = None

    def fetch_price_data(self):
        """Fetches the latest price data from the RSWiki API"""
        response = requests.get(self.base_url)
        response.raise_for_status()
        return response.json()

    def push_price_data_to_db(self, db_session):
        """Pushes the fetched price data to the database"""
        if self.priceData is None:
            raise ValueError("Price data has not been fetched yet.")

        # Assuming you have a SQLAlchemy model named PriceDataModel
        for item_id, data in self.priceData.items():
            price_record = PriceDataModel(
                id=item_id,
                name=data.get("name"),
                examine=data.get("examine"),
                price=data.get("price"),
                last=data.get("last"),
                volume=data.get("volume"),
                members=data.get("members"),
                lowalch=data.get("lowalch"),
                highalch=data.get("highalch"),
                limit=data.get("limit"),
                value=data.get("value"),
                icon=data.get("icon")
            )
            db_session.add(price_record)
        db_session.commit()



if __name__ == "__main__":
    price_data_service = RSWikiPriceData()
    price_data_service.priceData = price_data_service.fetch_price_data()
    print(dir(price_data_service.priceData))
    #print(price_data_service.priceData.keys())
    print()
    print(list(price_data_service.priceData.items())[0])