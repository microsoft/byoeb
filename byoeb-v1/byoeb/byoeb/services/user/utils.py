import hashlib
from byoeb_core.models.byoeb.user import User
from typing import List, Dict, Any

def get_experts_numbers(
    experts: Dict[str, List[str]]
) -> List[str]:
    # print("Experts: ", experts)
    # print("type: ", type(experts))
    combined_list = []
    for items in experts.values():
        if items:  # Check if the value is not None or empty
            combined_list.extend(items)
    return combined_list

def get_user_ids_from_phone_number_ids(
    phone_number_ids: List[str]
) -> List[str]:
    user_ids = []
    for phone_number_id in phone_number_ids:
        user_id = hashlib.md5(phone_number_id.encode()).hexdigest()
        user_ids.append(user_id)
    return user_ids

def get_missing_and_present_ids(
    ids: List[str],
    new_ids: List[str]    
):
    present_ids = []
    missing_ids = []
    for id in new_ids:
        if id not in ids:
            missing_ids.append(id)
        else:
            present_ids.append(id)
    return missing_ids, present_ids

def get_relations_update(
    ids: List[str],
    users: List[User]
) -> Dict[str, List[str]]:
    user_ids_relations_update: Dict[str, List[str]] = {}
    for user in users:
        relation_numbers = user.audience + get_experts_numbers(user.experts)
        user_ids = get_user_ids_from_phone_number_ids(relation_numbers)
        _, present_ids = get_missing_and_present_ids(ids, user_ids)
        for id in present_ids:
            if id not in user_ids_relations_update:
                user_ids_relations_update[id] = []
            user_ids_relations_update[id].append({
                "user_type": user.user_type,
                "phone_number_id": user.phone_number_id
            })
    affected_ids = list(user_ids_relations_update.keys())
    return affected_ids, user_ids_relations_update

def get_register_message(
    user: User,
    message
):
    return {
        "phone_number_id": user.phone_number_id,
        "type": user.user_type,
        "message": message,
    }

def get_delete_messages(
    phone_number_ids,
    missing_ids
):
    messages = []
    for phone_number_id in phone_number_ids:
        user_id = hashlib.md5(phone_number_id.encode()).hexdigest()
        if user_id in missing_ids:
            messages.append({
                "phone_number_id": phone_number_id,
                "message": "User not found"
            })
        else:
            messages.append({
                "phone_number_id": phone_number_id,
                "message": "Deleted successfully"
            })
    return messages