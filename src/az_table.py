import os
from azure.data.tables import TableServiceClient, TableClient
from azure.core.exceptions import ResourceExistsError


class PatientTable():

    def __init__(self):
        self.table_name = "PatientData"
        self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.table_service = TableServiceClient.from_connection_string(conn_str=self.connection_string)
        self.table_client = self.table_service.create_table_if_not_exists(self.table_name)


    def insert_data(self, entity):
        """Insert data into the table."""
        try:
            entity['PartitionKey'] = entity['MRD'].split('/')[0]
        except:
            entity['PartitionKey'] = 1
            
        entity['RowKey'] = entity['phone_number']
        try:
            self.table_client.create_entity(entity=entity)
            print(f"Entity inserted: {entity}")
        except ResourceExistsError:
            print("Entity already exists.")
        except Exception as e:
            print(f"Error inserting entity: {e}")

    def fetch_all_rows(self):
        """Fetch all rows from the table."""
        entities = self.table_client.list_entities()
        return list(entities)
    
    def delete_entity(self, partition_key, row_key):
        """Delete an entity from the table."""
        try:
            self.table_client.delete_entity(partition_key=partition_key, row_key=row_key)
            print(f"Entity deleted: PartitionKey={partition_key}, RowKey={row_key}")
        except Exception as e:
            print(f"Error deleting entity: {e}")

if __name__ == "__main__":
    patient_table = PatientTable()
    row = {
        "MRD": "SEHBLR/123454321",
        "name": "John Doe",
        "phone_number": "1234567890",
        "surgery_name": "CATARACT",
        "suregery_group_name": "Others",
        "age": 37,
        "gender": "male",
        "procedure_type": "Major Procedure",
        "surgery_date": "20-12-2024",
        "operating_doctor": "Hehe",
        "operating_doctor_number": "9987654321",
        "counsellor_name": "MSR counsellor",
        "counsellor_number": ""
    }

    patient_table.insert_data(row)