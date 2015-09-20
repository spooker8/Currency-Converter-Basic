//
//  ViewController.m
//  Peer 3
//
//  Created by Anand Kumar on 9/19/15.
//  Copyright © 2015 Anand Kumar. All rights reserved.
//

#import "ViewController.h"



@interface ViewController () <CRCurrencyRequestDelegate>

@end

@implementation ViewController

- (void)viewDidLoad {
    [super viewDidLoad];
    // Do any additional setup after loading the view, typically from a nib.
}


- (IBAction)buttonTapped:(id)sender {

    self.convertButton.enabled = NO;
    
    self.req = [[CRCurrencyRequest alloc] init];
    self.req.delegate = self;
    [self.req start];
}


-(void)currencyRequest:(CRCurrencyRequest *)req retrievedCurrencies:(CRCurrencyResults *)currencies
{
    
    self.convertButton.enabled = YES;
    
    double inputValue = [self.inputField.text floatValue];
    
    double euroValue = inputValue * currencies.EUR;
    double yenValue = inputValue * currencies.JPY;
    double gbpValue = inputValue * currencies.GBP;
 
    
    if (self.segmentController.selectedSegmentIndex==0)
        
    {
         NSString *euroCurrency = [NSString stringWithFormat:@"Euro %.2f", euroValue];
        
        self.outputField.text = euroCurrency;
        
    }
    
    else if (self.segmentController.selectedSegmentIndex==1)
    
    {
    NSString *jpyCurrency = [NSString stringWithFormat:@"Yen %.2f", yenValue];
        
        self.outputField.text = jpyCurrency;
    
    }
    
    else if (self.segmentController.selectedSegmentIndex==2)
        
    {
        
        NSString *gbpCurrency = [NSString stringWithFormat:@"British Pounds %.2f", gbpValue];
    
        self.outputField.text = gbpCurrency;
    }
}




- (void)didReceiveMemoryWarning {
    [super didReceiveMemoryWarning];
    // Dispose of any resources that can be recreated.
}

@end
