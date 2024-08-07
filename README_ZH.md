
# Data Interpreter (DI)

## 什么是 Data Interpreter
Data Interpreter 是一个通过代码解决数据相关问题的代理。它理解用户需求，制定计划，编写执行代码，并在必要时使用工具。

## 论文中的实验
### 安装
> 确保您的系统上已安装 Python 3.9+。您可以使用以下命令检查：`python --version`。
> 推荐使用 conda 环境：`conda create -n di python=3.9 && conda activate di`
> 我们使用 metagpt 作为开发 Data Interpreter 的依赖项。安装 metagpt 并在 `config/config2.yaml` 中配置 openai api key
```bash
pip install metagpt==0.8.1
# pip install metagpt[rag]==0.8.1  # 如果你想使用 experience
export PYTHONPATH="/absolute/path/to/this/repo:$PYTHONPATH"
```

### Data Interpreter 数据集结构

di_dataset

- ml_benchmark
    - 04_titanic
    - 05_house-prices-advanced-regression-techniques
    - 06_santander-customer-transaction-prediction
    - 07_icr-identify-age-related-conditions
    - 08_santander-value-prediction-challenge
- open_ended_tasks
    - 01_ocr
    - 02_ocr
    - 03_ocr
    - 14_image_background_removal
    - 16_image_2_code_generation
    - 17_image_2_code_generation
- MATH
    - 保持原始下载结构

### ML-Benchmark 数据集和需求

在运行实验之前，您可以下载数据集（表格中的链接），并将它们放置在指定路径 (`di_dataset`)。我们已经在 `di_dataset` 中下载了 `04_titanic` 数据集以供演示。

您需要运行 `split.py` 将数据集拆分为训练集和测试集
```bash
cd di_dataset/ml_benchmark
python split.py
cd ../..
```

ML-Benchmark 包含 8 个典型的机器学习数据集。

| ID | Task Name             | Dataset Name     | Link                                           | User Requirement                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
|----|-----------------------|------------------|------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 01 | 01_iris               | Iris             | Built-in sklearn dataset. No need to download. | Run data analysis on sklearn Iris dataset, include a plot                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 02 | 02_wines_recognition  | Wine recognition |       Built-in sklearn dataset. No need to download.                                         | Run data analysis on sklearn Wine recognition dataset, include a plot, and train a model to predict wine class with 20% as test set, and show prediction accuracy                                                                                                                                                                                                                                                                                                                                                                                                                                |
| 03 | 03_breast_cancer      | Breast Cancer    |             Built-in sklearn dataset. No need to download.                                   | Run data analysis on sklearn Wisconsin Breast Cancer dataset, include a plot, train a model to predict targets (20% as validation), and show validation accuracy                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 04 | 04_titanic            | Titanic          | [link](https://www.kaggle.com/competitions/titanic/data)                                       | This is a titanic passenger survival dataset, your goal is to predict passenger survival outcome. The target column is Survived. Perform data analysis, data preprocessing, feature engineering, and modeling to predict the target. Report accuracy on the eval data. Train data path: '{data_dir}/ml_benchmark/4_titanic/split_train.csv', eval data path: '{data_dir}/ml_benchmark/04_titanic/split_eval.csv'.                                                                                                                                                                                |
| 05 | 05_house_prices       | House Prices     | [link](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/data)                                       | This is a house price dataset, your goal is to predict the sale price of a property based on its features. The target column is SalePrice. Perform data analysis, data preprocessing, feature engineering, and modeling to predict the target. Report RMSE between the logarithm of the predicted value and the logarithm of the observed sales price on the eval data. Train data path: '{data_dir}/ml_benchmark/05_house-prices-advanced-regression-techniques/split_train.csv', eval data path: '{data_dir}/ml_benchmark/05_house-prices-advanced-regression-techniques/split_eval.csv'.      |
| 06 | 06_santander_customer | Santander Customer | [link](https://www.kaggle.com/competitions/santander-customer-transaction-prediction/data)                                       | This is a customers financial dataset. Your goal is to predict which customers will make a specific transaction in the future. The target column is target. Perform data analysis, data preprocessing, feature engineering, and modeling to predict the target. Report AUC on the eval data. Train data path: '{data_dir}/ml_benchmark/06_santander-customer-transaction-prediction/split_train.csv', eval data path: '{data_dir}/ml_benchmark/06_santander-customer-transaction-prediction/split_eval.csv' .                                                                                    |
| 07 | 07_icr_identify       | ICR - Identifying | [link](https://www.kaggle.com/competitions/icr-identify-age-related-conditions/data)                                       | This is a medical dataset with over fifty anonymized health characteristics linked to three age-related conditions. Your goal is to predict whether a subject has or has not been diagnosed with one of these conditions. The target column is Class. Perform data analysis, data preprocessing, feature engineering, and modeling to predict the target. Report F1 Score on the eval data. Train data path: '{data_dir}/ml_benchmark/07_icr-identify-age-related-conditions/split_train.csv', eval data path: '{data_dir}/ml_benchmark/07_icr-identify-age-related-conditions/split_eval.csv' . |
| 08 | 08_santander_value    | Santander Value  | [link](https://www.kaggle.com/competitions/santander-value-prediction-challenge/data)                                       | This is a customers financial dataset. Your goal is to predict the value of transactions for each potential customer. The target column is target. Perform data analysis, data preprocessing, feature engineering, and modeling to predict the target. Report RMSLE on the eval data. Train data path: '{data_dir}/ml_benchmark/08_santander-value-prediction-challenge/split_train.csv', eval data path: '{data_dir}/ml_benchmark/08_santander-value-prediction-challenge/split_eval.csv' .                                                                                                     |

**注意**:
1. `data_dir` 是存储 `di_dataset` 的目录。

要重现论文中的结果，请运行以下命令：

```bash
python examples/run_ml_benchmark.py --task_name 04_titanic
```

一些关键参数：

- `--task_name`: 必需，指定要运行的任务。例如，04_titanic 和 14_image_background_removal。有关可用任务名称，请参阅下表。
- `--data_dir`: 可选，存储 `di_dataset` 的目录（默认为 `.`，当前工作目录）。
- `--use_reflection`: 可选，是否使用反射的标志（默认为 True）。
- `--use_experience`: 可选，是否使用经验的标志（默认为 False）。

### Open-Ended Tasks 数据集和需求

Open-Ended Tasks 收集并设计了 20 个中等难度的开放式任务，要求 Data Interpreters 理解用户需求，计划和分解任务，并生成和执行代码。


| ID | Task Name                   | Scenario                           | Scenario Description                                                                                                                                    | User Requirement                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
|----|-----------------------------|------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 01 | 01_ocr                      | OCR                                | Scan all the necessary fields and amounts from the given file and then create an Excel sheet with the extracted data.                                   | This is an English invoice image. Your goal is to perform OCR on the image, extract the total amount from ocr result and save as table, using PaddleOCR. The PaddleOCR environment has been fully installed, try to use Paddleocr as much as possible. Image path: '{data_dir}/open_ended_tasks/01_ocr.png                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| 02 | 02_ocr                      | OCR                                | Scan all the necessary fields and amounts from the given file and then create an Excel sheet with the extracted data.                                   | This is a Chinese invoice image. Your goal is to perform OCR on the image and only output the recognized text word results, nothing else is needed, then extract the total amount and receipt ID starting with 'No' from ocr text words results and save as table, using PaddleOCR. The PaddleOCR environment has been fully installed, try to use Paddleocr as much as possible. Image path: '{data_dir}/open_ended_tasks/02_ocr.jpg'                                                                                                                                                                                                                                                                                                                                                                    |
| 03 | 03_ocr                      | OCR                                | Scan all the necessary fields and amounts from the given file and then create an Excel sheet with the extracted data.                                   | This is an invoice image for OCR. Your goal is to perform OCR on the image, extract the total amount and save it into an Excel table format, using PaddleOCR with lang='en' The PaddleOCR environment has been fully installed, try to use Paddleocr as much as possible. Image path: '{data_dir}/open_ended_tasks/03_ocr.jpg'                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| 04 | 04_web_search_and_crawling  | Web search and crawling            | Crawling and organizing web form information                                                                                                            | Get data from `paperlist` table in https://papercopic.com/statistics/iclr-statistics/iclr-2024-statistics/ , and save it to a csv file. paper title must include `multiagent` or `large language model`. **notice: print key variables**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 05 | 05_web_search_and_crawling  | Web search and crawling            | Crawling and organizing web form information                                                                                                            | Obtain the CPI data from https://www.stats.gov.cn/sj/sjjd/202307/t20230718_1941322.html, please follow this plan step by step: 1. Detect the encoding type and HTML structure of the target webpage. 2. Crawl the webpage, de-duplicate the body content, convert it to a clear paragraph suitable for reading as plain text, and save it to target.txt. 3. Design multiple regular expressions to match key sentences in target.txt, use try-except statements to combine the various regular expression matches, note that the webpage text is in Chinese. 4. Finally, use a Chinese summary to summarize the key sentences to answer the user's request. **Note: If it is a code block, print out the key variable results of the code block; if it is webpage text, print the first 200 characters.** |
| 06 | 06_web_search_and_crawling  | Web search and crawling            | Crawling and organizing web form information                                                                                                            | Get products data from website https://scrapeme.live/shop/ and save it as a csv file. Notice: Firstly parse the web page encoding and the text HTML structure; The first page product name, price, product URL, and image URL must be saved in the csv;                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| 07 | 07_web_search_and_crawling  | Web search and crawling            | Crawling and organizing web form information                                                                                                            | 从36kr创投平台https://pitchhub.36kr.com/financing-flash所有初创企业融资的信息, **注意: 这是⼀个中⽂⽹站**; 下⾯是⼀个⼤致流程, 你会根据每⼀步的运⾏结果对当前计划中的任务做出适当调整: 1. 爬取并本地保存html结构; 2. 直接打印第7个**快讯**关键词后2000个字符的html内容, 作为**快讯的html内容示例**; 3. 反思**快讯的html内容示例**中的规律, 设计正则匹配表达式**来获取快讯**的标题、链接、时间; 4. 筛选最近3天的初创企业融资**快讯**, 以list[dict]形式打印前5个。5. 将全部结果存在本地csv中                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| 08 | 08_email_reply              | Email reply                        | Filter through my emails and respond to them as necessary                                                                                               | You are an agent that automatically reads and replies to emails. I will give you your Outlook email account and password. You need to check the content of the latest email and return it to me. If the email address suffix of this email is @xxx.xxx, please automatically reply with "I've received your email and will reply as soon as possible. Thank you!" Email account: xxx@xxx.xxx Email Password: xxxx                                                                                                                                                                                                                                                                                                                                                                                         |
| 09 | 09_web_page_imitation       | Web page imitation                 | Using Selenium and WebDriver to access a webpage and convert it to an image, with the assistance of GPT-4V to mimic the creation of a one-page website. | This is a URL of webpage: https://medium.com/ .  Firstly, utilize Selenium and WebDriver for rendering. Secondly, convert image to a webpage including HTML, CSS and JS in one go. Finally, save webpage in a text file. All required dependencies and environments have been fully installed and configured.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| 10 | 10_web_page_imitation       | Web page imitation                 | Using Selenium and WebDriver to access a webpage and convert it to an image, with the assistance of GPT-4V to mimic the creation of a one-page website. | This is a URL of webpage: https://pytorch.org/ .  Firstly, utilize Selenium and WebDriver for rendering. Secondly, convert image to a webpage including HTML, CSS and JS in one go. Finally, save webpage in a file. NOTE: All required dependencies and environments have been fully installed and configured.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 11 | 11_web_page_imitation       | Web page imitation                 | Using Selenium and WebDriver to access a webpage and convert it to an image, with the assistance of GPT-4V to mimic the creation of a one-page website. | This is a URL of webpage: https://www.kaggle.com/ . Firstly, utilize Selenium and WebDriver to render the webpage, ensuring the browser window is maximized for an optimal viewing experience. Secondly, convert image to a webpage including HTML, CSS and JS in one go. Finally, save webpage in a file. NOTE: All required dependencies and environments have been fully installed and configured.                                                                                                                                                                                                                                                                                                                                                                                                     |
| 12 | 12_web_page_imitation       | Web page imitation                 | Using Selenium and WebDriver to access a webpage and convert it to an image, with the assistance of GPT-4V to mimic the creation of a one-page website. | This is a URL of webpage: https://chat.openai.com/auth/login . Firstly, utilize Selenium and WebDriver to render the webpage, ensuring the browser window is maximized for an optimal viewing experience. Secondly, convert image to a webpage including HTML, CSS and JS in one go. Finally, save webpage in a file. NOTE: All required dependencies and environments have been fully installed and configured.                                                                                                                                                                                                                                                                                                                                                                                          |
| 13 | 13_web_page_imitation       | Web page imitation                 | Using Selenium and WebDriver to access a webpage and convert it to an image, with the assistance of GPT-4V to mimic the creation of a one-page website. | This is a URL of webpage: https://deepmind.google/technologies/gemini/#introduction . Firstly, utilize Selenium and WebDriver to render the webpage, ensuring the browser window is maximized for an optimal viewing experience. Secondly, convert image to a webpage including HTML, CSS and JS in one go. Finally, save webpage in a file. NOTE: All required dependencies and environments have been fully installed and configured.                                                                                                                                                                                                                                                                                                                                                                   |
| 14 | 14_image_background_removal | Image Background Removal           | Remove the background of a given image                                                                                                                  | This is an image, you need to use python toolkit rembg remove the background of the image. image path:'{data_dir}/open_ended_tasks/14_image_background_removal.jpg'; save path:'{data_dir}/open_ended_tasks/14_image_background_removal.jpg'                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| 15 | 15_text2img                 | Text2Img                           | Use SD tools to generate images                                                                                                                         | I want to generate an image of a beautiful girl using the stable diffusion text2image tool, sd_url = "http://your.sd.service.ip:port"                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| 16 | 16_image_2_code_generation  | Image2Code Generation              | Web code generation                                                                                                                                     | This is a image. First, convert the image to webpage code including HTML, CSS and JS in one go, and finally save webpage code in a file.The image path: '{data_dir}/open_ended_tasks/16_image_2_code_generation.png'. NOTE: All required dependencies and environments have been fully installed and configured.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| 17 | 17_image_2_code_generation  | Image2Code Generation              | Web code generation                                                                                                                                     | This is a image. First, convert the image to webpage code including HTML, CSS and JS in one go, and finally save webpage code in a file.The image path: '{data_dir}/open_ended_tasks/16_image_2_code_generation.png'. NOTE: All required dependencies and environments have been fully installed and configured.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| 18 | 18_generate_games           | Generate games using existing repo | Game tool usage (pyxel)                                                                                                                                 | Create a Snake game. Players need to control the movement of the snake to eat food and grow its body, while avoiding the snake's head touching their own body or game boundaries. Games need to have basic game logic, user interface. During the production process, please consider factors such as playability, beautiful interface, and convenient operation of the game. Note: pyxel environment already satisfied                                                                                                                                                                                                                                                                                                                                                                                   |
| 19 | 19_generate_games           | Generate games using existing repo | Game tool usage (pyxel)                                                                                                                                 | You are a professional game developer, please use pyxel software to create a simple jumping game. The game needs to include a character that can move left and right on the screen. When the player presses the spacebar, the character should jump. Please ensure that the game is easy to operate, with clear graphics, and complies with the functional limitations of pyxel software. Note: pyxel environment already satisfied                                                                                                                                                                                                                                                                                                                                                                       |
| 20 | 20_generate_games           | Generate games using existing repo | Game tool usage (pyxel)                                                                                                                                 | Make a mouse click game that click button as many times as possible in 30 seconds using pyxel. Note: pyxel environment already satisfied                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |

**注意**：
1. `data_dir` 是存储 `di_dataset` 的目录。
2. 需要在 `requirements_prompt.py` 中将具体的电子邮件账号和密码替换为实际的电子邮件账号和密码。
3. 需要在 `requirements_prompt.py` 中将具体的 `sd_url` 替换为实际的 `sd_url`。
4. 与“使用现有仓库生成游戏”和数学基准相关的代码正在集成中，敬请期待。


要重现论文中的结果，请运行以下命令：

```bash
python examples/run_open_ended_tasks.py --task_name 14_image_background_removal
```

### 数学数据集和要求

- 下载 [**数学数据集**](https://people.eecs.berkeley.edu/~hendrycks/MATH.tar)


- 将 tar 文件解压到 `di_dataset/MATH`

- 使用 `--categories` 选择要运行的类别，问题是从难度等级为 5 的问题中随机选择的。以下是类别名称和 ID。例如，您可以在数论（`--categories 4`）中测试难度等级为 5 的问题：

| ID | 类别名称                  |
|----|--------------------------|
| 0  | 代数                     |
| 1  | 计数与概率               |
| 2  | 几何                     |
| 3  | 中级代数                 |
| 4  | 数论                     |
| 5  | 初级代数                 |
| 6  | 预备微积分               |


要重现论文中的结果，请运行以下命令：

```bash
python examples/run_math_benchmark.py --categories 4 --level 5 --vote_num 3 --folder ./math_experiment --dataset_path ./di_dataset/MATH
```
您可以在文件夹 `./math_experiment` 中找到实验记录。


### SWE-bench 数据集和要求

SWE-bench 是一个测试系统自动解决 GitHub 问题能力的数据集。该数据集收集了来自 12 个流行 Python 项目的 2,294 个 Issue-Pull Request 对。

该数据集可在以下链接获取：[SWE-bench](https://huggingface.co/datasets/princeton-nlp/SWE-bench)

- 要运行 SWE-bench 数据集，您可以执行以下命令：

```bash
python examples/run_swe_agent_for_benchmark.py
```

此脚本用于执行 SWE-bench 数据集。它加载数据集，处理每个实例，并保存结果。


- 要修复实际的开放问题，您可以执行以下命令：

```bash
python examples/run_swe_agent_open_source_issue.py
```

此脚本用于修复实际的开放问题。它接受预定义的问题，处理它们，并尝试为指定的存储库生成修复。
