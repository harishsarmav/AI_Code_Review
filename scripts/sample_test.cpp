#include <iostream>
using namespace std;

class Test {
public:
    int* data;

    // Constructor
    Test() {
        data = new int[10];  // Uninitialized array (potential memory leak)
        cout << "Test object created" << endl;
    }

    // Destructor (Incorrect memory deallocation)
    ~Test() {
        delete data;  // Should be delete[] data
        cout << "Test object destroyed" << endl;
    }

    // Function with missing return value
    int getValue(int index) {
        if (index < 0 || index >= 10) {
            cout << "Index out of bounds!" << endl;
        }
        // Missing return statement, should return something
    }

    // Potential uninitialized variable usage
    void showValue() {
        int value;
        cout << "Value is: " << value << endl;  // Uninitialized 'value'
    }
};

int main() {
    Test testObj;

    testObj.getValue(15);  // Index out of bounds
    testObj.showValue();   // Uninitialized variable used

    return 0;
}
