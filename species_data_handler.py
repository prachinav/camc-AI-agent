import pandas as pd
from geopy.distance import geodesic
import os

class SpeciesLocationEngine:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(current_dir, "data")

        self.location_df = pd.read_csv(os.path.join(data_dir, "prachi_database.csv"))

        self.species_df = pd.read_csv(os.path.join(data_dir, "species_metadata.csv"))

        self.species_metadata = self.species_df.set_index('Code').to_dict('index')

    def find_nearby_studies(self, target_lat, target_lon, radius_km=200):
        nearby = []

        for _, row in self.location_df.iterrows():
            dist = geodesic((target_lat, target_lon), (row['y'], row['x'])).km
            if dist <= radius_km:
                nearby.append({
                    'distance_km': dist,
                    'country': row['country'],
                    'coordinates': (row['y'], row['x']),
                    'scores': {col: row[col] for col in self.species_metadata.keys() if col in row}
                })

        return sorted(nearby, key=lambda x: x['distance_km'])

    def recommend_species(self, nearby_studies, top_n=3):
        if not nearby_studies:
            return None

        species_stats = {}

        for study in nearby_studies:
            for species_code, score in study['scores'].items():
                if species_code not in species_stats:
                    species_stats[species_code] = {
                        'total_score': 0,
                        'study_count': 0,
                        'min_distance': study['distance_km'],
                        'countries': set()
                    }

                species_stats[species_code]['total_score'] += score
                species_stats[species_code]['study_count'] += 1
                species_stats[species_code]['countries'].add(study['country'])
                species_stats[species_code]['min_distance'] = min(
                    species_stats[species_code]['min_distance'],
                    study['distance_km']
                )

        recommendations = []
        for code, stats in species_stats.items():
            if code in self.species_metadata:
                metadata = self.species_metadata[code]
                recommendations.append({
                    'code': code,
                    'name': metadata.get('Genetic Material', code),  # Using 'Genetic Material' as name
                    'avg_score': stats['total_score'] / stats['study_count'],
                    'Frost Tolerance': metadata.get('Frost Tolerance', 'Unknown'),
                    'Dominant Height Mean': metadata.get('Dominant Heights (m) Mean', 'Unknown'),
                    'Number of Trials': metadata.get('Number of Trials', 0),
                    'Number of Trees': metadata.get('Number of Trees', 0),
                    'studies': stats['study_count'],
                    'closest_km': stats['min_distance'],
                    'countries': list(stats['countries'])
                })

        return sorted(recommendations, key=lambda x: -x['avg_score'])[:top_n]