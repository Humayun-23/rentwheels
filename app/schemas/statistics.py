from pydantic import BaseModel

class VehicleStatsResponse(BaseModel):
    total_vehicles: int
    
class ShopStatsResponse(BaseModel):
    total_shops: int

class BookingStatsResponse(BaseModel):
    total_bookings: int

class StatsSummaryResponse(BaseModel):
    total_shops: int
    total_vehicles: int
    total_bookings: int
