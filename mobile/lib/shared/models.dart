class UserModel {
  final int id;
  final String email;
  final bool isPro;
  UserModel({required this.id, required this.email, required this.isPro});

  factory UserModel.fromJson(Map<String, dynamic> json) =>
      UserModel(id: json['id'], email: json['email'], isPro: json['is_pro'] ?? false);
}

class VehicleModel {
  final int year;
  final String make;
  final String model;
  final String? trim;
  VehicleModel({required this.year, required this.make, required this.model, this.trim});

  factory VehicleModel.fromJson(Map<String, dynamic> json) => VehicleModel(
        year: json['year'],
        make: json['make'],
        model: json['model'],
        trim: json['trim'],
      );
}

class ListingModel {
  final int id;
  final String title;
  final num? price;
  final String? currency;
  final String? location;
  final VehicleModel vehicle;
  ListingModel({required this.id, required this.title, this.price, this.currency, this.location, required this.vehicle});

  factory ListingModel.fromJson(Map<String, dynamic> json) => ListingModel(
        id: json['id'] ?? json['listing_id'],
        title: json['title'],
        price: json['price'],
        currency: json['currency'],
        location: json['location'],
        vehicle: json['vehicle'] != null
            ? VehicleModel.fromJson(json['vehicle'])
            : VehicleModel(
                year: json['year'], make: json['make'], model: json['model'], trim: json['trim']),
      );
}