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

# 작업 방법
1. [github.com/IPCVLabEdu](https://github.com/IPCVLabEdu/assignments/tree/assignment_1)에서 개인 repository로 fork합니다. 
2. SourceTree를 사용하여 개인 repository에 fork한 주소를 local repository로 clone 해서 작업합니다.
3. master branch가 아닌 assignment_1 branch로 checkout 합니다. 
4. assginment_1 branch에서 `본인이름_ass1` banch를 새로 만듭니다. (e.g. `jaewon_ass1`)
5. `본인이름_ass1` branch에서 과제를 수행합니다.  
6. 과제 제출은 upstream(github.com/IPCVLabEdu)의 `본인이름_ass1`으로 Pull Request합니다. (자세한 사항은 [[결과제출 방법]](./How_to_submit_assignments.html)을 확인바랍니다.)



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
>다음 의사코드를 C++을 이용하여 구현합니다.  
![algorithm_2_3](https://user-images.githubusercontent.com/15168540/48592142-5542cd00-e98a-11e8-9fe9-a9bd007cb665.png)

#### **Result**

|**face model**|**input image**|**probability map**|
|:-:|:-:|:-:|
|<img src="https://user-images.githubusercontent.com/15168540/49068530-52898700-f26a-11e8-84dc-6e6a2f40a601.png" alt="alt text" width="320" height="320">|<img src="https://user-images.githubusercontent.com/15168540/49068545-5c12ef00-f26a-11e8-951d-609268fa52b6.png" alt="alt text" width="320" height="320">|<img src="https://user-images.githubusercontent.com/15168540/49068569-68974780-f26a-11e8-920b-170fb998982e.png" alt="alt text" width="320" height="320">|

## 결과 제출
[[결과제출 방법]](./How_to_submit_assignments.html)


[이전](../)
