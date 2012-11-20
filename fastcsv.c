#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <stdlib.h>

// Timing
#include <time.h>


// Define constants

#define PAGE_SIZE 4096*1000

// Define states

#define ROW_START                   0
#define PRE_PADDING                 1
#define END_PADDING                 2
#define IN_QUOTED                   3
#define FIRST_QUOTE_OR_END_QUOTED   4
#define END_VALUE                   5
#define IN_UNQUOTED                 6
#define END_UNQUOTED                7
#define COMMA                       8
#define NON_VALUE_CR                9


void callback_value_print(char* value) {
    printf("Value: %s\n", value);
}
void callback_row_print() {
    printf("End Row\n");
}

int parse_string(char *chars, int rows, int max, void(*callback_value)(char *value), void(*callback_row)()) { 
    //if (rows < 1) {
    //    printf("Error: Can't parse less than one row\n");
    //    return -5;
    //}
    char *cur = chars;
    int char_pos = 0;
    int callback_row_count = 0;
    int state = ROW_START;
    char value[PAGE_SIZE+1];
    char *vcur = value;
    //while True:
        //chars = fp.read(4096)
        //if not chars:
        //    if row:
        //        if (callback_value != NULL) {
        //            callback_value(value)
        //        row.append(value)
        //        if (callback_row) {
        //            callback_row()
        //        else:
        //            row_data.append(row)
        //    return char_pos; //return char_pos, row_data
    while (char_pos<max) {
        //printf("%d %d %c\n", char_pos, state, *cur);
    //for char in chars: 
    //    #print char_pos, state, repr(char)
        switch (state) {
            case IN_QUOTED:
                switch (*cur) {
                    case '"':
                        state = FIRST_QUOTE_OR_END_QUOTED;
                        break;
                    default:
                        *vcur = *cur;
                        vcur++;
                        break;
                }
                break;
            case IN_UNQUOTED:
                switch (*cur) {
                    case '"':
                        //# printf("Warn: Found a '%c' character in an unquoted value at %d, assuming a quote was missed from the front of the value and continuing\n", *cur, char_pos);
                        state = FIRST_QUOTE_OR_END_QUOTED;
                        break;
                    case ',':
                        state = COMMA;
                        //row.append(value);
                        if (callback_value != NULL) {
                            // End the string
                            *vcur = '\0';
                            callback_value(value);
                            // Reset the pointer to re-use space
                            vcur = value;
                        }
                        //value = '';
                        break;
                    case ' ':
                        //# printf("Warn: Found a '%c' character in an unquoted value at %d, assuming the quoting was accidentally forgotten and continuing, expecting to a quote was missed from the front of the value and continuing\n", *cur, char_pos);
                        state = FIRST_QUOTE_OR_END_QUOTED;
                        break;
                    default:
                        *vcur = *cur;
                        vcur++;
                        break;
                }
                break;
            case ROW_START:
                switch (*cur) {
                    case '\n':
                        printf("Error: Expected \\r\\n at position %d, not \\n\n", char_pos);
                        return -1;
                    case '\r':
                        state = NON_VALUE_CR;
                        break;
                    case ',':
                        if (callback_value != NULL) {
                            // End the string
                            *vcur = '\0';
                            callback_value(value);
                            // Reset the pointer to re-use space
                            vcur = value;
                        }
                        //value = ''
                        state = COMMA;
                        break;
                    case '"':
                        state = IN_QUOTED;
                        break;
                    case ' ':
                        state = PRE_PADDING;
                        break;
                    default:
                        state = IN_UNQUOTED;
                        *vcur = *cur;
                        vcur++;
                        break;
                }
                break;
            case PRE_PADDING:
                switch (*cur) {
                    case ' ':
                        // No point in going around the whole state loop, let's just strip these quickly    
                        while (*cur == ' ') {
                            cur++;
                            char_pos +=1;
                        }
                        // # XXX Depending on the implementation, might want to add this:
                        // # *vcur = *cur
                        break;
                    case '\r':
                        state = NON_VALUE_CR;
                        break;
                    case ',':
                        //# printf("Warn: We found a '%c' at the end of a row at %d, assuming that it was supposed to be '\\r\\n' and continuing\n", *cur, char_pos);

                        if (callback_value != NULL) {
                            // End the string
                            *vcur = '\0';
                            callback_value(value);
                            // Reset the pointer to re-use space
                            vcur = value;
                        }
                        //row.append(value)
                        //value = ''
                        state = COMMA;
                        break;
                    case '\n':
                        //# printf("Warn: We found a '%c' at the end of a row at %d, assuming that it was supposed to be '\\r\\n' and continuing\n", *cur, char_pos);

                        if (callback_value != NULL) {
                            // End the string
                            *vcur = '\0';
                            callback_value(value);
                            // Reset the pointer to re-use space
                            vcur = value;
                        }
                        //row.append(value);
                        if (callback_row) {
                            callback_row();
                        }
                        //else {
                        //    row_data.append(row);
                        //}
                        callback_row_count += 1;
                        if ((rows > 0) && (callback_row_count >= rows)) {
                            return char_pos; //return char_pos, row_data;
                        }
                        //row = []
                        //value = ''
                        state = ROW_START;
                        break;
                    case '"':
                        state = IN_QUOTED;
                        break;
                    default:
                        state = IN_UNQUOTED;
                        *vcur = *cur;
                        vcur++;
                        break;
                }
                break;
            case FIRST_QUOTE_OR_END_QUOTED:
                switch (*cur) {
                    case '"':
                        state = IN_QUOTED;
                        *vcur = *cur;
                        vcur++;
                        break;
                    case ' ':
                        state = END_PADDING;
                        break;
                    case '\r':
                        state = NON_VALUE_CR;
                        break;
                    case '\n':
                        //# printf("Warn: We found a '%c' at the end of a row at %d, assuming that it was supposed to be '\\r\\n' and continuing\n", *cur, char_pos);

                        if (callback_value != NULL) {
                            // End the string
                            *vcur = '\0';
                            callback_value(value);
                            // Reset the pointer to re-use space
                            vcur = value;
                        }
                        //row.append(value);
                        if (callback_row) {
                            callback_row();
                        } 
                        //else {
                        //    row_data.append(row);
                        //}
                        callback_row_count += 1;
                        if ((rows > 0) && (callback_row_count >= rows)) {
                            return char_pos; //return char_pos, row_data
                        }
                        //row = []
                        //value = ''
                        state = ROW_START;
                        break;
                    case ',':
                        state = COMMA;
                        if (callback_value != NULL) {
                            // End the string
                            *vcur = '\0';
                            callback_value(value);
                            // Reset the pointer to re-use space
                            vcur = value;
                        }
                        //row.append(value)
                        //value = ''
                        break;
                    default:
                        printf("Error: Expected a second '\"' character at %d or a comma or space, not '%c'.\n", char_pos, *cur);
                        return -2;
                }
                break;
            case END_PADDING:
                switch (*cur) {
                    case ' ':
                        // No point in going around the whole state loop, let's just strip these quickly    
                        while (*cur == ' ') {
                            cur++;
                            char_pos +=1;
                        }
                        break;
                    case ',':
                        state = COMMA;
                        break;
                    case '\r':
                        state = NON_VALUE_CR;
                        break;
                    case '\n':
                        //# printf("Warn: We found a '\\n' at the end of a row at %d, assuming that it was supposed to be '\\r\\n' and continuing\n", char_pos);
                        if (callback_value != NULL) {
                            // End the string
                            *vcur = '\0';
                            callback_value(value);
                            // Reset the pointer to re-use space
                            vcur = value;
                        }
                        //row.append(value)
                        if (callback_row) {
                            callback_row();
                        }
                        //else {
                        //    row_data.append(row);
                        //}
                        callback_row_count += 1;
                        if ((rows > 0) && (callback_row_count >= rows)) {
                            return char_pos; //return char_pos, row_data
                        }
                        //row = []
                        //value = ''
                        state = ROW_START;
                        break;
                    default:
                        printf("Error: Expected a comma, space or newline after the padding at %d, not a '%c'\n", char_pos, *cur);
                        return -3;
                }
                break;
            case COMMA:
                switch (*cur) {
                    case '\n':
                        //# printf("Warn: We found a '\\n' at the end of a row at %d, assuming that it was supposed to be '\\r\\n' and continuing\n", char_pos);
                        if (callback_value != NULL) {
                            // End the string
                            *vcur = '\0';
                            callback_value(value);
                            // Reset the pointer to re-use space
                            vcur = value;
                        }
                        //row.append(value)
                        if (callback_row) {
                            callback_row();
                        } 
                        //else {
                        //    row_data.append(row);
                        //}
                        callback_row_count += 1;
                        if ((rows > 0) && (callback_row_count >= rows)) {
                            return char_pos; //return char_pos, row_data
                        }
                        //row = [];
                        //value = '';
                        state = ROW_START;
                        break;
                    case '\r':
                        state = NON_VALUE_CR;
                        break;
                    case ' ':
                        state = PRE_PADDING;
                        break;
                    case '"':
                        state = IN_QUOTED;
                        break;
                    case ',':
                        if (callback_value != NULL) {
                            callback_value('\0');
                            // Reset the pointer to re-use space
                            vcur = value;
                        }
                        //row.append('');
                        break;
                    default:
                        state = IN_UNQUOTED;
                        *vcur = *cur;
                        vcur++;
                        break;
                }
                break;
            case NON_VALUE_CR:
                switch (*cur) {
                    case '\n':
                        if (callback_value != NULL) {
                            // End the string
                            *vcur = '\0';
                            callback_value(value);
                            // Reset the pointer to re-use space
                            vcur = value;
                        }
                        //row.append(value)
                        if (callback_row) {
                            callback_row();
                        }
                        //else {
                        //    row_data.append(row);
                        //}
                        callback_row_count += 1;
                        if ((rows > 0) && (callback_row_count >= rows)) {
                            return char_pos; //return char_pos, row_data
                        }
                        //row = [];
                        //value = '';
                        state = ROW_START;
                        break;
                    default:
                        printf("Error: Expected '\\r\\n' at position %d, not '\\r%c'\n", char_pos, *cur);
                        return -4;
                }
                break;
        }
        //printf("Looping %c %d\n", *cur, state);
        char_pos +=1;
        cur++;
    }
    return 0;
}

int lex(char *filename, int pos, int rows, void(*callback_value)(char *value), void(*callback_row)()) { 
    //int fd;
    //ssize_t ret, len = PAGE_SIZE;
    //ssize_t len = PAGE_SIZE;
    char data[PAGE_SIZE+1];
    char *buf;
    buf = data;

FILE * pFile;
pFile = fopen ( filename , "rb" );
//fseek ( pFile , pos , SEEK_SET );



//    fd = open(filename, O_RDONLY);
//    if (fd == -1) {
//        printf("Could not open the file %s\n", filename);
//        return -1;
//    }
    size_t nr;
    //size_t seek;
   // printf("streaming...\n");
    //FILE *stream = fdopen(fd, "O_RDONLY");
    if (pos) {
        //printf("Pos: %d\n", pos);
        fseek(pFile, pos, SEEK_SET);
        //printf("Seek: %d\n", seek);
    }

    //printf("Reading...\n");
    nr = fread(buf, 1, PAGE_SIZE+1, pFile);
    if (nr < 1) {
        printf("End of file");
    }
    *(buf+PAGE_SIZE) = '\0';
    //printf("NR: %d\n", nr);
    //while (len !=0 && (ret = read(fd, buf, len)) != 0) {
    //    if (ret == -1) {
    //        if (errno == EINTR) {
    //            continue;
    //        }
    //        printf("Error: %s\n", filename);
    //        perror("read");
    //        break;
    //    }
    //    len -= ret;
    //    buf += ret;
    //}
   // *buf = '\0';
  //  if (close(fd) == 1){
  //      perror("close");
  //  }
    //printf("[INFO] Parsing %d characters ...\n", PAGE_SIZE);
    int res = parse_string(buf, rows, PAGE_SIZE, callback_value, callback_row);
    //printf("%s", buf);
    //printf("[INFO] Result: %d\n", res);
    //if (callback_value != NULL){
    //    callback_value(data);
    //}
    //if (callback_row != NULL){
    //    callback_row();
    //}
    //printf("[INFO] done.\n");
//    fclose(stream);
fclose ( pFile );
    return res;
}

int main(int argc, char **argv){
    int res;
    clock_t start = clock(), diff;
    //res = lex("bigtest.csv", 0, 640, NULL, NULL);
    res = lex("page/data.csv", 0, 2, callback_value_print, callback_row_print);
    diff = clock() - start;
    int msec = diff * 1000 / CLOCKS_PER_SEC;
    printf("[INFO] Time taken %d seconds %d milliseconds\n", msec/1000, msec%1000);
    return res;
}
