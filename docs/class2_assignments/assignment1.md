---
layout: default
---

# Assignment #1

---
# Setup
- Recommendation
    - [OpenCV](https://opencv.org/) : 4.0.0
    - OS : Windows 10
    - Visual Studio 2015  
    - [SourceTree](https://www.sourcetreeapp.com/)
  
- C++ & OpenCV를 이용하여 작성 ([OpenCV Tutorial](https://docs.google.com/presentation/d/1Uv1geoOMUp7PI4ReuiN8SLE4I6BZglN1viCBqW3DB8Y/edit))
- Github 활용 ([Github Tutorial](https://opentutorials.org/course/2708))
  
---

### Q0 : OpenCV 접해보기
>이미지를 불러와서 constrast와 brightness를 바꿔보는 간단한 예제입니다.  
>**assignment1_0.cpp** 를 수행합니다.  
>[[참고자료](https://docs.opencv.org/4.0.0/d3/dc1/tutorial_basic_linear_transform.html)]

#### **Result**  

|**Original Image**|**Alpha: 1.1 , Beta: 50** |
|:-:|:-:|
|  <img src="https://user-images.githubusercontent.com/15168540/49067844-78ae2780-f268-11e8-86bd-43cd7a5f56d0.png" alt="alt text" width="320" height="320">| <img src="https://user-images.githubusercontent.com/15168540/49068196-713b4e00-f269-11e8-92f7-f8c1c4caed11.png" alt="alt text" width="320" height="320"> | 



### Q1 : 알고리즘 2-1 - 명암 영상에서 히스토그램 계산
>**assignment1_1.cpp** 를 수행합니다.  
>다음 의사코드를 C++을 이용하여 구현합니다.  

![algorithm_2_1](https://user-images.githubusercontent.com/15168540/48592075-0dbc4100-e98a-11e8-8f0e-346c7f2c252b.png)

#### **Result**

|**Original Image**|**Alpha: 1.1 , Beta: 50** |
|:-:|:-:|
|  <img src="https://user-images.githubusercontent.com/15168540/49067844-78ae2780-f268-11e8-86bd-43cd7a5f56d0.png" alt="alt text" width="320" height="320">| <img src="https://user-images.githubusercontent.com/15168540/49068196-713b4e00-f269-11e8-92f7-f8c1c4caed11.png" alt="alt text" width="320" height="320"> |
|  <img src="https://user-images.githubusercontent.com/15168540/49068354-dbec8980-f269-11e8-9380-75026a2d4f79.png" alt="alt text" width="320" height="320">| <img src="https://user-images.githubusercontent.com/15168540/49068392-f888c180-f269-11e8-9232-fb0aa9e7e8e8.png" alt="alt text" width="320" height="320"> |  


### Q2 : 알고리즘 2-2 - 2차원 히스토그램 계산(HS 공간)
>**assignment1_2.cpp** 를 수행합니다.  
>다음 의사코드를 C++을 이용하여 구현합니다.  
![algorithm_2_2](https://user-images.githubusercontent.com/15168540/48592136-52e07300-e98a-11e8-8e82-46063e3afc41.png)

### Q3 : 알고리즘 2-3 - 히스토그램 역투영
>**assignment1_2.cpp** 를 수행합니다.  
>**참고사항 : 역투영하고자 하는 입력 이미지는 직접 선정하여 samples 폴더에 넣습니다**  
>**주의사항 : 새롭게 추가된 입력이미지는 git에 commit하지 않습니다.**  
>다음 의사코드를 C++을 이용하여 구현합니다.  
![algorithm_2_3](https://user-images.githubusercontent.com/15168540/48592142-5542cd00-e98a-11e8-9fe9-a9bd007cb665.png)

#### **Result**

|**face model**|**input image**|**probability map**|
|:-:|:-:|:-:|
|<img src="https://user-images.githubusercontent.com/15168540/49068530-52898700-f26a-11e8-84dc-6e6a2f40a601.png" alt="alt text" width="320" height="320">|<img src="https://user-images.githubusercontent.com/15168540/49068545-5c12ef00-f26a-11e8-951d-609268fa52b6.png" alt="alt text" width="320" height="320">|<img src="https://user-images.githubusercontent.com/15168540/49068569-68974780-f26a-11e8-920b-170fb998982e.png" alt="alt text" width="320" height="320">|

## 결과 제출   
 **결과 제출은 [여기](http://visual.kangwon.ac.kr/assignment)를 눌러주세요.**

  


[이전](../../)
