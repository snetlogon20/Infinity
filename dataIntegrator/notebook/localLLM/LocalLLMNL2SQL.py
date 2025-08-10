##############################################
# 正式开始
##############################################
from transformers import Trainer, TrainingArguments

# 第一步
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from datasets import load_dataset

# 指定版本（如 "refs/convert/parquet" 是官方维护的稳定分支）
# dataset = load_dataset(
#     "Salesforce/wikisql",
#     trust_remote_code=True,
#     revision="refs/convert/parquet"
# )
# print(dataset["train"][0])  # 查看数据结构
dataset = load_dataset(
    "Salesforce/wikisql",
    trust_remote_code=True,
    revision="refs/convert/parquet",
    split={
        "train": "train[:5%]",  # 前10%训练数据（约5,600条）
        "validation": "validation[:5%]"  # 前5%验证数据（约420条）
    }
)

# 第二步
from transformers import DataCollatorForSeq2Seq
from transformers import T5Tokenizer, T5ForConditionalGeneration, TrainingArguments

model_name = "t5-small"
tokenizer = T5Tokenizer.from_pretrained(model_name)
model = T5ForConditionalGeneration.from_pretrained(model_name)


# 3. 改进的预处理函数
def preprocess_function(examples):
    inputs = [f"translate English to SQL: {q}" for q in examples["question"]]
    # 构造 SQL 目标语句
    targets = []
    for i in range(len(examples["sql"])):
        sql_info = examples["sql"][i]
        selected_col = examples["table"][i]["header"][sql_info["sel"]]
        # 处理 WHERE 条件（限制最多 2 个条件）
        conditions = []
        for col_idx, op_idx, value in zip(
                sql_info["conds"]["column_index"][:2],  # 截断条件数量
                sql_info["conds"]["operator_index"][:2],
                sql_info["conds"]["condition"][:2]
        ):
            col_name = examples["table"][i]["header"][col_idx]
            op = ["=", ">", "<", "LIKE"][op_idx]
            conditions.append(f"{col_name} {op} {repr(value)}")
        where_clause = " AND ".join(conditions)
        target_sql = f"SELECT {selected_col} FROM table"
        if where_clause:
            target_sql += f" WHERE {where_clause}"
        targets.append(target_sql)
    # 统一填充到固定长度
    model_inputs = tokenizer(
        inputs,
        max_length=128,
        truncation=True,
        padding="max_length",  # 强制填充
        return_tensors="pt"
    )
    labels = tokenizer(
        targets,
        max_length=128,
        truncation=True,
        padding="max_length",  # 强制填充
        return_tensors="pt"
    )
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

# 4. 数据预处理
tokenized_dataset = dataset.map(
    preprocess_function,
    batched=True,
    batch_size=1000,  # 优化内存占用
    remove_columns=dataset["train"].column_names
)

# 5. 配置专用数据整理器
data_collator = DataCollatorForSeq2Seq(
    tokenizer=tokenizer,
    model=model,
    padding=True,
    pad_to_multiple_of=8  # 优化 GPU 内存对齐
)

# 6. 训练参数优化
# training_args = TrainingArguments(
#     output_dir=rf"D:\workspace_python\infinity_data\model\t5-small-result",
#     learning_rate=2e-5,
#     per_device_train_batch_size=8,
#     num_train_epochs=3,
#     weight_decay=0.01,
#     logging_dir=rf"D:\workspace_python\infinity_data\model\t5-small-result\logs",
#     fp16=True,                  # 启用混合精度训练
#     gradient_accumulation_steps=2,  # 梯度累积
#     dataloader_drop_last=True  # 丢弃不完整批次[3,8](@ref)
# )

training_args = TrainingArguments(
    output_dir=rf"D:\workspace_python\infinity_data\model\t5-small-result",
    learning_rate=2e-5,
    per_device_train_batch_size=4,  # 减小批次大小（原为8）
    num_train_epochs=1,            # 减少训练轮次（原为3）
    gradient_accumulation_steps=4,  # 梯度累积补偿小批次
    fp16=True,                     # 混合精度加速
    dataloader_drop_last=True,
    logging_steps=50               # 减少日志频率
)


# 7. 初始化 Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    eval_dataset=tokenized_dataset["validation"],
    data_collator=data_collator,  # 关键修复[3,4](@ref)
    tokenizer=tokenizer
)

# 8. 启动训练
trainer.train()


# 9. 保存模型
import torch
model_save_path = rf"D:\workspace_python\infinity_data\model\t5-small-finetuned"
torch.save(model.state_dict(), model_save_path)

model.save_pretrained(model_save_path)
tokenizer.save_pretrained(model_save_path)

# 10. 评测
eval_results = trainer.evaluate()
print(f"Validation Loss: {eval_results['eval_loss']:.4f}")


from transformers import T5ForConditionalGeneration, T5Tokenizer

# 加载训练后的模型（output_dir为训练时的输出路径）
model = T5ForConditionalGeneration.from_pretrained(rf"D:\workspace_python\infinity_data\model\t5-small-result\checkpoint-176")
tokenizer = T5Tokenizer.from_pretrained("t5-small")  # 或使用训练时保存的分词器



def generate_sql(question, max_length=100, num_beams=4):
    inputs = tokenizer(question, return_tensors="pt", padding=True, truncation=True)
    outputs = model.generate(
        inputs["input_ids"],
        max_length=max_length,
        num_beams=num_beams,
        early_stopping=True
    )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

# 示例输入
question = "What is the average salary of employees in the 'Engineering' department?"
sql_query = generate_sql(question)
print("Generated SQL:", sql_query)