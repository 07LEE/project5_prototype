"""
A
"""
from pathlib import Path
import re
import torch
import numpy as np

from .ner_tokenize import ner_tokenizer

DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"

def get_ner_predictions(text, checkpoint, device=DEVICE):
    """
    Predicts named entity tags for the given text using the provided NER model and tokenizer.
    """
    model = checkpoint['model']
    tokenizer = checkpoint['tokenizer']
    tag2id = checkpoint['tag2id']

    model.eval()
    text = text.replace(' ', '_')

    predictions, true_labels = [], []

    tokenized_sent = ner_tokenizer(text, len(text) + 2, tokenizer)
    input_ids = torch.tensor(tokenized_sent['input_ids']).unsqueeze(0).to(device)
    attention_mask = torch.tensor(tokenized_sent['attention_mask']).unsqueeze(0).to(device)
    token_type_ids = torch.tensor(tokenized_sent['token_type_ids']).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids)

    logits = outputs['logits']
    logits = logits.detach().cpu().numpy()
    label_ids = token_type_ids.cpu().numpy()

    predictions.extend([list(p) for p in np.argmax(logits, axis=2)])
    true_labels.append(label_ids)

    pred_tags = [list(tag2id.keys())[p_i] for p in predictions for p_i in p]

    return tokenized_sent, pred_tags

def show_tokens(text, checkpoint):
    """
    문장을 넣어서 토큰을 확인합니다.
    """
    tokenized_sent, pred_tags = get_ner_predictions(text, checkpoint)
    tokenizer = checkpoint['tokenizer']

    print('TOKEN \t TAG')
    print("===========")

    for i, tag in enumerate(pred_tags):
        # if tag != 'O':
        print("{:^5}\t{:^5}".format(
            tokenizer.convert_ids_to_tokens(tokenized_sent['input_ids'][i]), tag))

def read_file(file_list):
    """
    ner train을 위한 코드
    """
    token_docs = []
    tag_docs = []
    for file_path in file_list:
        # print("read file from ", file_path)
        file_path = Path(file_path)
        raw_text = file_path.read_text().strip()
        raw_docs = re.split(r'\n\t?\n', raw_text)
        for doc in raw_docs:
            tokens = []
            tags = []
            for line in doc.split('\n'):
                if line[0:1] == "$" or line[0:1] == ";" or line[0:2] == "##":
                    continue
                try:
                    token = line.split('\t')[0]
                    tag = line.split('\t')[3]   # 2: pos, 3: ner
                    for i, syllable in enumerate(token):    # 음절 단위로 잘라서
                        tokens.append(syllable)
                        modi_tag = tag
                        if i > 0:
                            if tag[0] == 'B':
                                modi_tag = 'I' + tag[1:]    # BIO tag를 부착할게요 :-)
                        tags.append(modi_tag)
                except:
                    print(line)
            token_docs.append(tokens)
            tag_docs.append(tags)

    return token_docs, tag_docs

def extract_entities(text, model, device, tokenizer):
    entities = []
    current_entity = ""
    current_tag = ""

    for i, tag in enumerate(pred_tags):
        token = tokenizer.convert_ids_to_tokens(tokenized_sent['input_ids'][i]).replace("##", "")

        if tag.startswith("B-"):
            if current_entity and current_tag != "O":
                entities.append(current_entity)
            current_entity = token
            current_tag = tag[2:]
        elif tag.startswith("I-"):
            if current_entity and tag[2:] == current_tag:
                current_entity += token
        else:
            if current_entity and current_tag != "O":
                entities.append(current_entity)
            current_entity = ""
            current_tag = ""

    if current_entity and current_tag != "O":
        entities.append(current_entity)

    return entities