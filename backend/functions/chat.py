from django.http import HttpResponse, HttpRequest
from backend.utils.response import (
    HttpMethod,
    invalid_request_method,
    error_response,
    success_response,
    unauthorized_request,
)
from os import path
from json import loads, dumps
from openai import OpenAI

from backend.models import Task, Object, Action, Location
from backend.utils.date import getDateTimeNow
from django.db.models import Q
from django.contrib.auth.models import User
from enum import Enum
from typing import Tuple
from backend.functions.task import EventsItems, LibrariesItems, LogicItems, StepsItems
import os

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("The OPENAI_API_KEY environment variable is not set.")
client = OpenAI(api_key=api_key)

CHATGPT_MODEL = "gpt-4o"
CHATGPT_TEMPERATURE = 0.2

CHATGPT_INSTRUCTIONS = """
You are an assistant designed to extract intent from text. You must drive the user to define a Pick-and-Place task for a collaborative robot providing to him/her the details to be defined before he/she asks for them.
Do not include any explanations, just provide an RFC8259 compliant JSON response that follows this format without deviation:
{
    answer: string,
    task: {
        program: {
            control: {
                control_type: string | null,
                times: number | null,
                event: {
                    event_type: string | null,
                    find_object: string | null,
                },
                otherwise: {
                    otherwise_pick: {
                        object: string | null
                    },
                    otherwise_processing: {
                    action: string | null
                    },
                    otherwise_place: {
                        location: string | null
                    },
                },
                control_pick: {
                    object: string | null
                },
                control_processing: {
                    action: string | null
                },
                control_place: {
                    location: string | null
                },
            },
            pick: {
                object: string | null
            },
            processing: {
                action: string | null
            },
            place: {
                location: string | null
            }
        }
    },
    finished: boolean
}
IMPORTANT: the 'answer' field is mandatory and must be filled with a string.

Explaination of the context:
- The user is not a roboticist or IT expert and he/she needs to create a task for a cobot to help him/her define pick and place tasks.
- To define a task, the user has to specify the pick object and the place location. The user can also specify an action to be performed on the object.
- The user can also specify a control intent to define a condition to be satisfied before the pick and place task can be executed.

Resume specifications:
- When you have collected all the information, you need to present a resume of the task you have just created to the user.
- You must ask to the user to confirm the summary or ask for changes.
- If the user wants to make changes, you must ask the modifications required and propose the updated resume asking again to check it.

Conclusion specifications:
- Only after the user has approved the resume, you must set to true the 'finished' property in the JSON.

General instructions:
- You can't left empty the 'answer' field.
- The 'answer' field in the JSON is your natural language response to the user. If you're unsure of an answer, you can ask the user to repeat the request.
"""

CHATGPT_USE_FUNCTIONS = "Only use the functions you have been provided with."
CHATGPT_ALWAYS_REPLY = "Always reply to the user. You can't left the property 'answer' blank. If you're unsure of an answer, you can ask the user to repeat the request."

CHATGPT_FUNCTION = {
    "name": "parse_chatgpt_response",
    "description": "Process response from chatgpt to digest information",
    "parameters": {
        "type": "object",
        "properties": {
            "answer": {"type": "string", "description": "Model response to the user"},
            "task": {
                "type": "object",
                "properties": {
                    "program": {
                        "type": "object",
                        "properties": {
                            "control": {
                                "type": "object",
                                "properties": {
                                    "control_type": {
                                        "type": "string",
                                        "enum": [
                                            "repeat",
                                            "loop",
                                            "when",
                                            "when_otherwise",
                                            # "stop_when",
                                            # "do_when",
                                        ],
                                        "description": "The control type of the control intent.",
                                    },
                                    "times": {
                                        "type": "integer",
                                        "description": "The times of repetition in the case of repeat control type.",
                                    },
                                    "otherwise": {
                                        "type": "object",
                                        "properties": {
                                            "otherwise_pick": {
                                                "type": "object",
                                                "properties": {
                                                    "object": {
                                                        "type": "string",
                                                        "description": "The object of the pick intent.",
                                                    }
                                                },
                                                "required": ["object"],
                                            },
                                            "otherwise_processing": {
                                                "type": "object",
                                                "properties": {
                                                    "action": {
                                                        "type": "string",
                                                        "description": "The action of the action intent.",
                                                    }
                                                },
                                                "required": ["action"],
                                            },
                                            "otherwise_place": {
                                                "type": "object",
                                                "properties": {
                                                    "location": {
                                                        "type": "string",
                                                        "description": "The location of the place intent.",
                                                    }
                                                },
                                                "required": ["location"],
                                            },
                                        },
                                        "required": ["pick", "place"],
                                    },
                                    "event": {
                                        "type": "object",
                                        "properties": {
                                            "event_type": {
                                                "type": "string",
                                                "enum": ["sensor", "find", "human"],
                                                # "enum": ["detect", "sensor", "find", "human"],
                                                "description": "The event type of the event intent.",
                                            },
                                            "find_object": {
                                                "type": "string",
                                                "description": "Object to find in the case of find event type.",
                                            },
                                        },
                                        "required": ["event_type"],
                                    },
                                    "control_pick": {
                                        "type": "object",
                                        "properties": {
                                            "object": {
                                                "type": "string",
                                                "description": "The object of the pick intent.",
                                            }
                                        },
                                        "required": ["object"],
                                    },
                                    "control_processing": {
                                        "type": "object",
                                        "properties": {
                                            "action": {
                                                "type": "string",
                                                "description": "The action of the action intent.",
                                            }
                                        },
                                        "required": ["action"],
                                    },
                                    "control_place": {
                                        "type": "object",
                                        "properties": {
                                            "location": {
                                                "type": "string",
                                                "description": "The location of the place intent.",
                                            }
                                        },
                                        "required": ["location"],
                                    },
                                },
                                "required": ["control_type"],
                            }
                        },
                        "required": ["control"],
                    }
                },
                "required": ["program"],
            },
            "finished": {
                "type": "boolean",
                "description": "The finished intent after the user has approved the resume",
            },
        },
        "required": ["answer", "task", "finished"],
    },
}

CHATGPT_ERROR = "A problem occurred while creating the new message. Please try again."


def new_message(request: HttpRequest) -> HttpResponse:
    try:
        if request.user.is_authenticated:
            if request.method == HttpMethod.POST.value:
                data = loads(request.body)
                message = data.get("message")
                chat_log = data.get("chatLog")
                fine_tuned_model = data.get("fineTunedModel")
                fine_tuning_job_id = data.get("fineTuningJobId")

                data_result = {}

                # Init the conversation
                if chat_log is None or len(chat_log) == 0:
                    """
                    # Check fine-tuned model
                    try:
                        job = openai.FineTuningJob.retrieve(fine_tuning_job_id)
                        fine_tuned_model = job["fine_tuned_model"]
                    except Exception:
                        job = None

                    if job is None:
                        file_path = path.join(
                            path.dirname(path.dirname(path.abspath(__file__))),
                            "functions",
                            "fine_tuning_tasks.jsonl",
                        )
                        file = openai.File.create(
                            file=open(file_path, "rb"),
                            purpose="fine-tune",
                        )

                        job = openai.FineTuningJob.create(
                            training_file=file["id"],
                            model="gpt-3.5-turbo",
                            suffix="blocklyGPT-tasks",
                        )

                        fine_tuning_job_id = job["id"]
                        fine_tuned_model = job["fine_tuned_model"]
                        print("NEW MODEL CREATED")
                        print("Model ID: " + fine_tuned_model)
                        print("Job ID: " + fine_tuning_job_id)
                    """
                    chat_log = [
                        {
                            "role": "system",
                            "content": CHATGPT_INSTRUCTIONS,
                        },
                        {"role": "system", "content": CHATGPT_USE_FUNCTIONS},
                        {"role": "system", "content": CHATGPT_ALWAYS_REPLY},
                    ]

                chat_log.append({"role": "user", "content": message})
                response = client.chat.completions.create(
                    model=CHATGPT_MODEL,
                    messages=chat_log,
                    temperature=CHATGPT_TEMPERATURE,
                    functions=[CHATGPT_FUNCTION],
                    function_call={"name": CHATGPT_FUNCTION["name"]},
                )

                response_json = response.choices[0].message.function_call.arguments

                try:
                    response_json = loads(response_json)
                    answer = response_json["answer"]

                    if answer != "":
                        chat_log.append({"role": "assistant", "content": answer})

                    # Response has the "answer" field blank
                    i = 0
                    while not answer:
                        if (
                            i > 2
                        ):  # I can't use ChatGPT API more than 3 times in a minute
                            # print("FORCE EXIT LOOP NO answer")
                            forced_answer = "Ok! Let's go ahead."
                            chat_log.append(
                                {"role": "assistant", "content": forced_answer}
                            )
                            break

                        # print("LOOP NO answer")
                        # print(response_json)
                        chat_log.append(
                            {"role": "system", "content": CHATGPT_ALWAYS_REPLY}
                        )
                        response = client.chat.completions.create(
                            model=CHATGPT_MODEL,
                            messages=chat_log,
                            temperature=CHATGPT_TEMPERATURE,
                            functions=[CHATGPT_FUNCTION],
                            function_call={"name": CHATGPT_FUNCTION["name"]},
                        )

                        response_json = response.choices[
                            0
                        ].message.function_call.arguments

                        response_json = loads(response_json)
                        answer = response_json["answer"]
                        i += 1

                except Exception:
                    data_result["answer"] = CHATGPT_ERROR

                data_result["chatLog"] = chat_log
                data_result["response"] = response_json
                data_result["fineTunedModel"] = fine_tuned_model
                data_result["fineTuningJobId"] = fine_tuning_job_id
                return success_response(data_result)
            else:
                return invalid_request_method()
        else:
            return unauthorized_request()
    except Exception as e:
        print(e)
        return error_response(CHATGPT_ERROR)


class ChatLogicItems(Enum):
    REPEAT = "repeat"
    LOOP = "loop"
    WHEN_OTHERWISE = "when_otherwise"
    WHEN = "when"
    # STOP_WHEN = "stop_when"
    # DO_WHEN = "do_when"


class ChatEventItems(Enum):
    SENSOR = "sensor"
    FIND = "find"
    HUMAN = "human"
    # DETECT = "detect"


def save_chat_task(request: HttpRequest) -> HttpResponse:
    try:
        if request.user.is_authenticated:
            if request.method == HttpMethod.POST.value:
                user = User.objects.get(id=request.user.id)
                data = loads(request.body)
                task_id = data.get("id")
                taskStructure = data.get("taskStructure")

                taskCode = {}

                # Repeat and Loop
                if (
                    taskStructure["program"]["control"]["control_type"]
                    == ChatLogicItems.REPEAT.value
                    or taskStructure["program"]["control"]["control_type"]
                    == ChatLogicItems.LOOP.value
                ):
                    if (
                        taskStructure["program"]["control"]["control_type"]
                        == ChatLogicItems.REPEAT.value
                    ):
                        taskCode = {
                            "type": LogicItems.REPEAT.value,
                            "fields": {
                                "times": taskStructure["program"]["control"]["times"]
                            },
                        }
                    else:
                        taskCode = {
                            "type": LogicItems.LOOP.value,
                        }

                    object_name_to_search = None
                    if (
                        taskStructure["program"]["control"]["control_pick"]["object"]
                        is not None
                    ):
                        object_name_to_search = taskStructure["program"]["control"][
                            "control_pick"
                        ]["object"]
                    else:
                        object_name_to_search = taskStructure["program"]["pick"][
                            "object"
                        ]

                    object_id, object_name, object_keywords = search_existing_libraries(
                        user,
                        Object,
                        object_name_to_search,
                    )

                    location_name_to_search = None
                    if (
                        taskStructure["program"]["control"]["control_place"]["location"]
                        is not None
                    ):
                        location_name_to_search = taskStructure["program"]["control"][
                            "control_place"
                        ]["location"]
                    else:
                        location_name_to_search = taskStructure["program"]["place"][
                            "location"
                        ]
                    (
                        location_id,
                        location_name,
                        location_keywords,
                    ) = search_existing_libraries(
                        user, Location, location_name_to_search
                    )

                    if (
                        taskStructure["program"]["control"]["control_processing"][
                            "action"
                        ]
                        is not None
                        or taskStructure["program"]["processing"]["action"] is not None
                    ):
                        action_name_to_search = None
                        if (
                            taskStructure["program"]["control"]["control_processing"][
                                "action"
                            ]
                            is not None
                        ):
                            action_name_to_search = taskStructure["program"]["control"][
                                "control_processing"
                            ]["action"]
                        else:
                            action_name_to_search = taskStructure["program"][
                                "processing"
                            ]["action"]
                        (
                            action_id,
                            action_name,
                            action_keywords,
                        ) = search_existing_libraries(
                            user,
                            Action,
                            action_name_to_search,
                        )
                        taskCode["inputs"] = {
                            "DO": {
                                "block": {
                                    "type": StepsItems.PICK.value,
                                    "inputs": {
                                        "OBJECT": {
                                            "block": {
                                                "type": LibrariesItems.OBJECT.value,
                                                "data": dumps(
                                                    {
                                                        "id": object_id,
                                                        "name": object_name,
                                                        "keywords": object_keywords,
                                                    }
                                                ),
                                                "fields": {"name": object_name},
                                            }
                                        }
                                    },
                                    "next": {
                                        "block": {
                                            "type": StepsItems.PROCESSING.value,
                                            "inputs": {
                                                "ACTION": {
                                                    "block": {
                                                        "type": LibrariesItems.ACTION.value,
                                                        "data": dumps(
                                                            {
                                                                "id": action_id,
                                                                "name": action_name,
                                                                "keywords": action_keywords,
                                                            }
                                                        ),
                                                        "fields": {"name": action_name},
                                                    }
                                                }
                                            },
                                            "next": {
                                                "block": {
                                                    "type": StepsItems.PLACE.value,
                                                    "inputs": {
                                                        "LOCATION": {
                                                            "block": {
                                                                "type": LibrariesItems.LOCATION.value,
                                                                "data": dumps(
                                                                    {
                                                                        "id": location_id,
                                                                        "name": location_name,
                                                                        "keywords": location_keywords,
                                                                    }
                                                                ),
                                                                "fields": {
                                                                    "name": location_name
                                                                },
                                                            }
                                                        }
                                                    },
                                                }
                                            },
                                        }
                                    },
                                }
                            }
                        }
                    else:
                        taskCode["inputs"] = {
                            "DO": {
                                "block": {
                                    "type": StepsItems.PICK.value,
                                    "inputs": {
                                        "OBJECT": {
                                            "block": {
                                                "type": LibrariesItems.OBJECT.value,
                                                "data": dumps(
                                                    {
                                                        "id": object_id,
                                                        "name": object_name,
                                                        "keywords": object_keywords,
                                                    }
                                                ),
                                                "fields": {"name": object_name},
                                            }
                                        }
                                    },
                                    "next": {
                                        "block": {
                                            "type": StepsItems.PLACE.value,
                                            "inputs": {
                                                "LOCATION": {
                                                    "block": {
                                                        "type": LibrariesItems.LOCATION.value,
                                                        "data": dumps(
                                                            {
                                                                "id": location_id,
                                                                "name": location_name,
                                                                "keywords": location_keywords,
                                                            }
                                                        ),
                                                        "fields": {
                                                            "name": location_name
                                                        },
                                                    }
                                                }
                                            },
                                        }
                                    },
                                }
                            }
                        }

                # When and When-Otherwise
                elif (
                    taskStructure["program"]["control"]["control_type"]
                    == ChatLogicItems.WHEN.value
                    or taskStructure["program"]["control"]["control_type"]
                    == ChatLogicItems.WHEN_OTHERWISE.value
                ):
                    # Control type
                    if (
                        taskStructure["program"]["control"]["control_type"]
                        == ChatLogicItems.WHEN.value
                    ):
                        taskCode = {
                            "type": LogicItems.WHEN.value,
                        }
                    else:
                        taskCode = {
                            "type": LogicItems.WHEN_OTHERWISE.value,
                        }

                    # Event type
                    # if (
                    #     taskStructure["program"]["control"]["event"]["event_type"]
                    #     == ChatEventItems.DETECT.value
                    # ):
                    #     taskCode["inputs"] = {
                    #         "WHEN": {
                    #             "block": {
                    #                 "type": EventsItems.DETECT.value,
                    #             }
                    #         }
                    #     }

                    if (
                        taskStructure["program"]["control"]["event"]["event_type"]
                        == ChatEventItems.SENSOR.value
                    ):
                        taskCode["inputs"] = {
                            "WHEN": {
                                "block": {
                                    "type": EventsItems.SENSOR.value,
                                }
                            }
                        }
                    elif (
                        taskStructure["program"]["control"]["event"]["event_type"]
                        == ChatEventItems.HUMAN.value
                    ):
                        taskCode["inputs"] = {
                            "WHEN": {
                                "block": {
                                    "type": EventsItems.HUMAN.value,
                                }
                            }
                        }
                    elif (
                        taskStructure["program"]["control"]["event"]["event_type"]
                        == ChatEventItems.FIND.value
                    ):
                        (
                            object_to_find_id,
                            object_to_find_name,
                            object_to_find_keywords,
                        ) = search_existing_libraries(
                            user,
                            Object,
                            taskStructure["program"]["control"]["event"]["find_object"],
                        )

                        taskCode["inputs"] = {
                            "WHEN": {
                                "block": {
                                    "type": EventsItems.FIND.value,
                                    "inputs": {
                                        "OBJECT": {
                                            "block": {
                                                "type": LibrariesItems.OBJECT.value,
                                            },
                                            "data": dumps(
                                                {
                                                    "id": object_to_find_id,
                                                    "name": object_to_find_name,
                                                    "keywords": object_to_find_keywords,
                                                }
                                            ),
                                            "fields": {"name": object_to_find_name},
                                        }
                                    },
                                }
                            }
                        }

                    object_name_to_search = None
                    if (
                        taskStructure["program"]["control"]["control_pick"]["object"]
                        is not None
                    ):
                        object_name_to_search = taskStructure["program"]["control"][
                            "control_pick"
                        ]["object"]
                    else:
                        object_name_to_search = taskStructure["program"]["pick"][
                            "object"
                        ]

                    object_id, object_name, object_keywords = search_existing_libraries(
                        user,
                        Object,
                        object_name_to_search,
                    )

                    location_name_to_search = None
                    if (
                        taskStructure["program"]["control"]["control_place"]["location"]
                        is not None
                    ):
                        location_name_to_search = taskStructure["program"]["control"][
                            "control_place"
                        ]["location"]
                    else:
                        location_name_to_search = taskStructure["program"]["place"][
                            "location"
                        ]
                    (
                        location_id,
                        location_name,
                        location_keywords,
                    ) = search_existing_libraries(
                        user, Location, location_name_to_search
                    )

                    if (
                        taskStructure["program"]["control"]["control_processing"][
                            "action"
                        ]
                        is not None
                        or taskStructure["program"]["processing"]["action"] is not None
                    ):
                        action_name_to_search = None
                        if (
                            taskStructure["program"]["control"]["control_processing"][
                                "action"
                            ]
                            is not None
                        ):
                            action_name_to_search = taskStructure["program"]["control"][
                                "control_processing"
                            ]["action"]
                        else:
                            action_name_to_search = taskStructure["program"][
                                "processing"
                            ]["action"]
                        (
                            action_id,
                            action_name,
                            action_keywords,
                        ) = search_existing_libraries(
                            user,
                            Action,
                            action_name_to_search,
                        )
                        taskCode["inputs"].update(
                            {
                                "DO": {
                                    "block": {
                                        "type": StepsItems.PICK.value,
                                        "inputs": {
                                            "OBJECT": {
                                                "block": {
                                                    "type": LibrariesItems.OBJECT.value,
                                                    "data": dumps(
                                                        {
                                                            "id": object_id,
                                                            "name": object_name,
                                                            "keywords": object_keywords,
                                                        }
                                                    ),
                                                    "fields": {"name": object_name},
                                                }
                                            }
                                        },
                                        "next": {
                                            "block": {
                                                "type": StepsItems.PROCESSING.value,
                                                "inputs": {
                                                    "ACTION": {
                                                        "block": {
                                                            "type": LibrariesItems.ACTION.value,
                                                            "data": dumps(
                                                                {
                                                                    "id": action_id,
                                                                    "name": action_name,
                                                                    "keywords": action_keywords,
                                                                }
                                                            ),
                                                            "fields": {
                                                                "name": action_name
                                                            },
                                                        }
                                                    }
                                                },
                                                "next": {
                                                    "block": {
                                                        "type": StepsItems.PLACE.value,
                                                        "inputs": {
                                                            "LOCATION": {
                                                                "block": {
                                                                    "type": LibrariesItems.LOCATION.value,
                                                                    "data": dumps(
                                                                        {
                                                                            "id": location_id,
                                                                            "name": location_name,
                                                                            "keywords": location_keywords,
                                                                        }
                                                                    ),
                                                                    "fields": {
                                                                        "name": location_name
                                                                    },
                                                                }
                                                            }
                                                        },
                                                    }
                                                },
                                            }
                                        },
                                    }
                                }
                            }
                        )
                    else:
                        taskCode["inputs"].update(
                            {
                                "DO": {
                                    "block": {
                                        "type": StepsItems.PICK.value,
                                        "inputs": {
                                            "OBJECT": {
                                                "block": {
                                                    "type": LibrariesItems.OBJECT.value,
                                                    "data": dumps(
                                                        {
                                                            "id": object_id,
                                                            "name": object_name,
                                                            "keywords": object_keywords,
                                                        }
                                                    ),
                                                    "fields": {"name": object_name},
                                                }
                                            }
                                        },
                                        "next": {
                                            "block": {
                                                "type": StepsItems.PLACE.value,
                                                "inputs": {
                                                    "LOCATION": {
                                                        "block": {
                                                            "type": LibrariesItems.LOCATION.value,
                                                            "data": dumps(
                                                                {
                                                                    "id": location_id,
                                                                    "name": location_name,
                                                                    "keywords": location_keywords,
                                                                }
                                                            ),
                                                            "fields": {
                                                                "name": location_name
                                                            },
                                                        }
                                                    }
                                                },
                                            }
                                        },
                                    }
                                }
                            }
                        )

                    # Otherwise
                    if (
                        taskStructure["program"]["control"]["control_type"]
                        == ChatLogicItems.WHEN_OTHERWISE.value
                    ):
                        (
                            object_otherwise_id,
                            object_otherwise_name,
                            object_otherwise_keywords,
                        ) = search_existing_libraries(
                            user,
                            Object,
                            taskStructure["program"]["control"]["otherwise"][
                                "otherwise_pick"
                            ]["object"],
                        )

                        (
                            location_otherwise_id,
                            location_otherwise_name,
                            location_otherwise_keywords,
                        ) = search_existing_libraries(
                            user,
                            Location,
                            taskStructure["program"]["control"]["otherwise"][
                                "otherwise_place"
                            ]["location"],
                        )

                        if (
                            taskStructure["program"]["control"]["otherwise"][
                                "otherwise_processing"
                            ]
                            is not None
                            and taskStructure["program"]["control"]["otherwise"][
                                "otherwise_processing"
                            ]["action"]
                        ):
                            (
                                action_otherwise_id,
                                action_otherwise_name,
                                action_otherwise_keywords,
                            ) = search_existing_libraries(
                                user,
                                Action,
                                taskStructure["program"]["control"]["otherwise"][
                                    "otherwise_processing"
                                ]["action"],
                            )
                            taskCode["inputs"].update(
                                {
                                    "OTHERWISE": {
                                        "block": {
                                            "type": StepsItems.PICK.value,
                                            "inputs": {
                                                "OBJECT": {
                                                    "block": {
                                                        "type": LibrariesItems.OBJECT.value,
                                                        "data": dumps(
                                                            {
                                                                "id": object_otherwise_id,
                                                                "name": object_otherwise_name,
                                                                "keywords": object_otherwise_keywords,
                                                            }
                                                        ),
                                                        "fields": {
                                                            "name": object_otherwise_name
                                                        },
                                                    }
                                                }
                                            },
                                            "next": {
                                                "block": {
                                                    "type": StepsItems.PROCESSING.value,
                                                    "inputs": {
                                                        "ACTION": {
                                                            "block": {
                                                                "type": LibrariesItems.ACTION.value,
                                                                "data": dumps(
                                                                    {
                                                                        "id": action_otherwise_id,
                                                                        "name": action_otherwise_name,
                                                                        "keywords": action_otherwise_keywords,
                                                                    }
                                                                ),
                                                                "fields": {
                                                                    "name": action_otherwise_name
                                                                },
                                                            }
                                                        }
                                                    },
                                                    "next": {
                                                        "block": {
                                                            "type": StepsItems.PLACE.value,
                                                            "inputs": {
                                                                "LOCATION": {
                                                                    "block": {
                                                                        "type": LibrariesItems.LOCATION.value,
                                                                        "data": dumps(
                                                                            {
                                                                                "id": location_otherwise_id,
                                                                                "name": location_otherwise_name,
                                                                                "keywords": location_otherwise_keywords,
                                                                            }
                                                                        ),
                                                                        "fields": {
                                                                            "name": location_otherwise_name
                                                                        },
                                                                    }
                                                                }
                                                            },
                                                        }
                                                    },
                                                }
                                            },
                                        }
                                    }
                                }
                            )
                        else:
                            taskCode["inputs"].update(
                                {
                                    "OTHERWISE": {
                                        "block": {
                                            "type": StepsItems.PICK.value,
                                            "inputs": {
                                                "OBJECT": {
                                                    "block": {
                                                        "type": LibrariesItems.OBJECT.value,
                                                        "data": dumps(
                                                            {
                                                                "id": object_otherwise_id,
                                                                "name": object_otherwise_name,
                                                                "keywords": object_otherwise_keywords,
                                                            }
                                                        ),
                                                        "fields": {
                                                            "name": object_otherwise_name
                                                        },
                                                    }
                                                }
                                            },
                                            "next": {
                                                "block": {
                                                    "type": StepsItems.PLACE.value,
                                                    "inputs": {
                                                        "LOCATION": {
                                                            "block": {
                                                                "type": LibrariesItems.LOCATION.value,
                                                                "data": dumps(
                                                                    {
                                                                        "id": location_otherwise_id,
                                                                        "name": location_otherwise_name,
                                                                        "keywords": location_otherwise_keywords,
                                                                    }
                                                                ),
                                                                "fields": {
                                                                    "name": location_otherwise_name
                                                                },
                                                            }
                                                        }
                                                    },
                                                }
                                            },
                                        }
                                    }
                                }
                            )

                # No controls
                elif taskStructure["program"]["control"]["control_type"] is None:
                    object_id, object_name, object_keywords = search_existing_libraries(
                        user,
                        Object,
                        taskStructure["program"]["pick"]["object"],
                    )

                    (
                        location_id,
                        location_name,
                        location_keywords,
                    ) = search_existing_libraries(
                        user,
                        Location,
                        taskStructure["program"]["place"]["location"],
                    )

                    taskCode = {
                        "type": StepsItems.PICK.value,
                    }

                    if (
                        taskStructure["program"]["processing"] is not None
                        and taskStructure["program"]["processing"]["action"]
                    ):
                        (
                            action_id,
                            action_name,
                            action_keywords,
                        ) = search_existing_libraries(
                            user,
                            Action,
                            taskStructure["program"]["processing"]["action"],
                        )
                        taskCode["inputs"] = {
                            "OBJECT": {
                                "block": {
                                    "type": LibrariesItems.OBJECT.value,
                                    "data": dumps(
                                        {
                                            "id": object_id,
                                            "name": object_name,
                                            "keywords": object_keywords,
                                        }
                                    ),
                                    "fields": {"name": object_name},
                                }
                            },
                        }
                        taskCode["next"] = {
                            "block": {
                                "type": StepsItems.PROCESSING.value,
                                "inputs": {
                                    "ACTION": {
                                        "block": {
                                            "type": LibrariesItems.ACTION.value,
                                            "data": dumps(
                                                {
                                                    "id": action_id,
                                                    "name": action_name,
                                                    "keywords": action_keywords,
                                                }
                                            ),
                                            "fields": {"name": action_name},
                                        }
                                    }
                                },
                                "next": {
                                    "block": {
                                        "type": StepsItems.PLACE.value,
                                        "inputs": {
                                            "LOCATION": {
                                                "block": {
                                                    "type": LibrariesItems.LOCATION.value,
                                                    "data": dumps(
                                                        {
                                                            "id": location_id,
                                                            "name": location_name,
                                                            "keywords": location_keywords,
                                                        }
                                                    ),
                                                    "fields": {"name": location_name},
                                                }
                                            }
                                        },
                                    }
                                },
                            },
                        }
                    else:
                        taskCode["inputs"] = {
                            "OBJECT": {
                                "block": {
                                    "type": LibrariesItems.OBJECT.value,
                                    "data": dumps(
                                        {
                                            "id": object_id,
                                            "name": object_name,
                                            "keywords": object_keywords,
                                        }
                                    ),
                                    "fields": {"name": object_name},
                                }
                            },
                        }
                        taskCode["next"] = {
                            "block": {
                                "type": StepsItems.PLACE.value,
                                "inputs": {
                                    "LOCATION": {
                                        "block": {
                                            "type": LibrariesItems.LOCATION.value,
                                            "data": dumps(
                                                {
                                                    "id": location_id,
                                                    "name": location_name,
                                                    "keywords": location_keywords,
                                                }
                                            ),
                                            "fields": {"name": location_name},
                                        }
                                    }
                                },
                            },
                        }

                date = getDateTimeNow()

                Task.objects.filter(id=task_id).update(
                    code=dumps(taskCode),
                    last_modified=date,
                )
                return success_response()
            else:
                return invalid_request_method()
        else:
            return unauthorized_request()
    except Exception as e:
        return error_response(str(e))


def search_existing_libraries(
    user: User, type: Object | Location | Action, name: str
) -> Tuple[int, str, str]:
    # Object
    if type == Object:
        object = (
            Object.objects.filter(Q(owner=user) | Q(shared=True))
            .filter(name__iexact=name)
            .first()
        )

        if object is not None:
            keywords = None
            if object.keywords:
                keywords = ",".join(object.keywords)
            return object.id, object.name, keywords
        else:
            # Search for keywords
            objectsOfUser = Object.objects.filter(Q(owner=user) | Q(shared=True))

            object_match_keyword = None
            for object in objectsOfUser:
                if object.keywords:
                    lowercase_keywords = [
                        keyword.lower() for keyword in object.keywords
                    ]
                    if name.lower() in lowercase_keywords:
                        object_match_keyword = object
                        break

            if object_match_keyword is not None:
                return (
                    object_match_keyword.id,
                    object_match_keyword.name,
                    ",".join(object_match_keyword.keywords),
                )
            else:
                return None, name, None

    # Location
    elif type == Location:
        location = (
            Location.objects.filter(Q(owner=user) | Q(shared=True))
            .filter(name__iexact=name)
            .first()
        )

        if location is not None:
            keywords = None
            if location.keywords:
                keywords = ",".join(location.keywords)
            return location.id, location.name, keywords
        else:
            # Search for keywords
            locationsOfUser = Location.objects.filter(Q(owner=user) | Q(shared=True))

            location_match_keyword = None
            for location in locationsOfUser:
                if location.keywords:
                    lowercase_keywords = [
                        keyword.lower() for keyword in location.keywords
                    ]
                    if name.lower() in lowercase_keywords:
                        location_match_keyword = location
                        break

            if location_match_keyword is not None:
                return (
                    location_match_keyword.id,
                    location_match_keyword.name,
                    ",".join(location_match_keyword.keywords),
                )
            else:
                return None, name, None

    # Action
    elif type == Action:
        action = (
            Action.objects.filter(Q(owner=user) | Q(shared=True))
            .filter(name__iexact=name)
            .first()
        )

        if action is not None:
            keywords = None
            if action.keywords:
                keywords = ",".join(action.keywords)
            return action.id, action.name, keywords
        else:
            # Search for keywords
            actionsOfUser = Action.objects.filter(Q(owner=user) | Q(shared=True))

            action_match_keyword = None
            for action in actionsOfUser:
                if action.keywords:
                    lowercase_keywords = [
                        keyword.lower() for keyword in action.keywords
                    ]
                    if name.lower() in lowercase_keywords:
                        action_match_keyword = action
                        break

            if action_match_keyword is not None:
                return (
                    action_match_keyword.id,
                    action_match_keyword.name,
                    ",".join(action_match_keyword.keywords),
                )
            else:
                return None, name, None
